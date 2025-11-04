""" A utility for generating tilted board layouts and rendering them in Excalidraw
Used for generating cutting diagrams for woodworking projects.

How it works: Two tilted lines for each board intersecting a rectangular frame define the edges of a board. 
If the frame corners are between the two lines, they are also included in the board shape.
The board points are then sorted in clockwise order around the board center to form a polygon.
"""

from excaligen.DiagramBuilder import DiagramBuilder
from abc import ABC, abstractmethod
from typing import Self

import math

Point = tuple[float, float]
Board = list[Point]

Frame = tuple[Point, Point, Point, Point]

class TiltedLine:
    """ Represents a line tilted at a certain angle and offset from the origin"""
    def __init__(self, angle: float, offset: float):
        self.angle = angle
        self.slope = math.tan(angle)
        self.intercept = -self.slope * offset

    def intersect_frame(self, frame: Frame) -> list[Point] | None:
        for i in range(4):
            p1 = frame[i]
            p2 = frame[(i + 1) % 4]
            intersection = self.intersect_aa_line(p1, p2)
            if intersection is not None:
                yield intersection

    def is_point_between_lines(self, point: Point, other: "TiltedLine") -> bool:
        (x, y) = point
        y1 = self.slope * x + self.intercept
        y2 = other.slope * x + other.intercept
        return y >= min(y1, y2) and y <= max(y1, y2)

    def intersect_aa_line(self, p1: Point, p2: Point) -> Point | None:
        (x1, y1) = p1
        (x2, y2) = p2
        if math.isclose(x1, x2):
            x = x1
            y = self.slope * x + self.intercept
            if y >= min(y1, y2) and y <= max(y1, y2):
                return (x, y)
            else:
                return None
        elif math.isclose(y1, y2):
            y = y1
            x = (y - self.intercept) / self.slope
            if x >= min(x1, x2) and x <= max(x1, x2):
                return (x, y)
            else:
                return None
        
        else:
            raise ValueError("Non axis-aligned line segment is not supported")

class Layout(ABC):
    """ Calculates the layout of boards in a tilted frame"""
    def __init__(self, width, height, board_width, angle, spacing):
        self.angle = math.radians(angle)
        self.width = width
        self.height = height
        self.frame = ((-width / 2, -height / 2), (width / 2, -height / 2), (width / 2, height / 2), (-width / 2, height / 2))
        self.offset_step = board_width / math.sin(self.angle) + spacing / math.sin(self.angle)
        self.board_x_half_width = board_width / math.sin(self.angle) / 2
        self.boards: list[Board] = []
        self.top_offsets: list[(float, float)] = []
        self.bottom_offsets: list[(float, float)] = []
        self.left_offsets: list[(float, float)] = []
        self.right_offsets: list[(float, float)] = []

    def calculate(self) -> Self:
        """ Calculate the layout of boards in the frame"""
        offset = self.setup()
        while True:
            offset += self.offset_step
            board = self._try_create_board(offset)
            if board is None:
                break
            
            board2 = self._try_create_board(-offset)
            if board2 is None:
                break

            self.boards.append(board)
            self.boards.append(board2)

        self._calculate_offsets()
        return self

    @abstractmethod
    def setup(self) -> float:
        pass

    def _try_create_board(self, offset) -> Board | None:
        """ Try to create a board at a given offset. Returns None if the board is out of frame"""
        center = (offset, 0)
        xmin = offset - self.board_x_half_width
        xmax = offset + self.board_x_half_width
        line1 = TiltedLine(self.angle, xmin)
        line2 = TiltedLine(self.angle, xmax)
        intersections1 = list(line1.intersect_frame(self.frame))
        intersections2 = list(line2.intersect_frame(self.frame))
        if len(intersections1) == 0 and len(intersections2) == 0:
            return None

        board = []

        for corner in self.frame:
            if line1.is_point_between_lines(corner, line2):
                board.append(corner)

        board.extend(intersections1)
        board.extend(intersections2)
        board = self._sort_board_points(board, center)

        return board

    def _sort_board_points(self, board: Board, center: Point) -> Board:
        """ Sort board points in clockwise order around the center point"""
        (cx, cy) = center
        def angle_from_center(point: Point) -> float:
            (x, y) = point
            return math.atan2(y - cy, x - cx)
        return sorted(board, key = angle_from_center)

    def _calculate_offsets(self):
        """ Calculate offsets of borads touching the frame edges"""
        for board in self.boards:
            for (x, y) in board:
                if math.isclose(y, -self.height / 2):
                    self._append_offset(self.bottom_offsets, x, self.width / 2)
                if math.isclose(y, self.height / 2):
                    self._append_offset(self.top_offsets, x, self.width / 2)
                if math.isclose(x, -self.width / 2):
                    self._append_offset(self.left_offsets, y, self.height / 2)
                if math.isclose(x, self.width / 2):
                    self._append_offset(self.right_offsets, y, self.height / 2)

    def _append_offset(self, offsets: list[(float, float)], value: float, shift: float):
        offsets.append((value, value + shift))

class EvenLayout(Layout):
    """ Layout with even number of boards"""
    def setup(self) -> float:
        return -self.offset_step / 2
    
class OddLayout(Layout):
    """ Layout with odd number of boards"""
    def setup(self) -> float:
        self.boards.append(self._try_create_board(0.0))
        return 0.0

class Renderer:
    """ Renders the layout using Excalidraw"""
    def __init__(self, layout: Layout) -> None:
        self.layout = layout

    def render(self, basename: str):
        """ Render the layout to an Excalidraw file"""
        xd = DiagramBuilder()
        xd.defaults().sloppiness('architect').roundness('sharp').thickness('thin').color("black")
        for board in self.layout.boards:
            transformed_board = [(x, -y) for (x, y) in board] # Invert Y axis for Excalidraw

            xd.line().points(transformed_board).close().background('brown').fill('solid')

        xd.save(self._create_filename(basename))

    def blueprint(self, basename: str):
        """ Render the layout as a blueprint to an Excalidraw file"""
        xd = DiagramBuilder()
        xd.defaults().sloppiness('architect').roundness('sharp').thickness('thin').color("black").font('Nunito')
        for board in self.layout.boards:
            transformed_board = [(x, -y) for (x, y) in board] # Invert Y axis for Excalidraw
            xd.line().points(transformed_board).close()
            self._render_board_dimensions(xd, transformed_board)

        self._render_border_offsets(xd)

        xd.save(self._create_filename(basename))

    def _create_filename(self, basename: str) -> str:
        if not basename.endswith(".excalidraw"):
            basename += ".excalidraw"
        return basename
    
    def _render_board_dimensions(self, xd: DiagramBuilder, board: Board) -> None:
        for i in range(len(board) - 1):
            a = board[i]
            b = board[i + 1]
            length = math.hypot(b[0] - a[0], b[1] - a[1])
            normal_vector = ((b[1] - a[1]) / length, -(b[0] - a[0]) / length)
            mid_point = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)

            multiplier = -1.0 if self._is_border_line(a, b) else 1.0
            x = mid_point[0] + normal_vector[0] * multiplier * 25
            y = mid_point[1] + normal_vector[1] * multiplier * 25

            xd.text().content(self._format_dimension(length)).center(x, y).color("blue")

    def _format_dimension(self, value: float) -> str:
        return f"{value:.1f}"
    
    def _is_border_line(self, a: Point, b: Point) -> bool:
        return (math.isclose(a[0], b[0]) or math.isclose(a[1], b[1]))
    
    def _render_border_offsets(self, xd: DiagramBuilder) -> None:
        offsets = sorted(self.layout.top_offsets)
        increment = 0
        for (x1, x2) in offsets:
            y = -self.layout.height / 2 - 5
            y1 = y - 30 - increment
            xd.line().points([(x1, y), (x1, y1)]).color("green")
            xd.text().content(self._format_dimension(x2)).color("green").anchor(x1 - 3, y1, 'right', 'top')
            increment += 30

        offsets = sorted(self.layout.bottom_offsets)
        increment = 0
        for (x1, x2) in offsets:
            y = self.layout.height / 2 + 5
            y1 = y + 30 + increment
            xd.line().points([(x1, y), (x1, y1)]).color("green")
            xd.text().content(self._format_dimension(x2)).color("green").anchor(x1 - 3, y1, 'right', 'bottom')
            increment += 30

        offsets = sorted(self.layout.left_offsets)
        increment = 0
        for (y1, y2) in offsets:
            x = -self.layout.width / 2 - 5
            x1 = x - 50 - increment
            xd.line().points([(x, -y1), (x1, -y1)]).color("green")
            xd.text().content(self._format_dimension(y2)).color("green").anchor(x1, -y1, 'left', 'top')
            increment += 60

        offsets = sorted(self.layout.right_offsets)
        increment = 0
        for (y1, y2) in offsets:
            x = self.layout.width / 2 + 5
            x1 = x + 50 + increment
            xd.line().points([(x, -y1), (x1, -y1)]).color("green")
            xd.text().content(self._format_dimension(y2)).color("green").anchor(x1, -y1, 'right', 'top')
            increment += 60


if __name__ == "__main__":
    even_layout = EvenLayout(600, 400, 140, 45, 4)
    renderer = Renderer(even_layout.calculate())
    renderer.render("layout_even")
    renderer.blueprint("layout_even_blueprint")

    odd_layout = OddLayout(600, 400, 140, 45, 4)
    renderer = Renderer(odd_layout.calculate())
    renderer.render("layout_odd")
    renderer.blueprint("layout_odd_blueprint")



