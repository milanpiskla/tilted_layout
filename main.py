""" A utility for generating tilted board layouts and rendering them in Excalidraw
Used for generating cutting diagrams for woodworking projects.

How it works: Two tilted lines for each board intersecting a rectangular frame define the edges of a board. 
If the frame corners are between the two lines, they are also included in the board shape.
The board points are then sorted in clockwise order around the board center to form a polygon.
"""

from excaligen.DiagramBuilder import DiagramBuilder
from abc import ABC, abstractmethod

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
        self.frame = ((-width / 2, -height / 2), (width / 2, -height / 2), (width / 2, height / 2), (-width / 2, height / 2))
        self.offset_step = board_width / math.sin(self.angle) + spacing / math.sin(self.angle)
        self.board_x_half_width = board_width / math.sin(self.angle) / 2
        self.boards: list[Board] = []

    def calculate(self) -> list[Board] | None:
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

        return self.boards

    @abstractmethod
    def setup(self) -> float:
        pass

    def _try_create_board(self, offset) -> Board | None:
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
        (cx, cy) = center
        def angle_from_center(point: Point) -> float:
            (x, y) = point
            return math.atan2(y - cy, x - cx)
        return sorted(board, key = angle_from_center)
    
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
    def __init__(self, boards: list[Board]) -> None:
        self.boards = boards

    def render(self, basename = "layout.excalidraw"):
        xd = DiagramBuilder()
        for board in self.boards:
            transformed_board = [(x, -y) for (x, y) in board] # Invert Y axis for Excalidraw

            xd.line().sloppiness('architect').roundness('sharp').points(transformed_board).close().color("#000000").thickness('thin').background('brown')

        xd.save(basename)


if __name__ == "__main__":
    even_layout = EvenLayout(600, 400, 140, 22, 4)
    renderer = Renderer(even_layout.calculate())
    renderer.render("layout_even.excalidraw")

    odd_layout = OddLayout(600, 400, 140, 22, 4)
    renderer = Renderer(odd_layout.calculate())
    renderer.render("layout_odd.excalidraw")



