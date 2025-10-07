from excaligen.DiagramBuilder import DiagramBuilder

import math

Point = tuple[float, float]
Board = list[Point]

Frame = tuple[Point, Point, Point, Point]

class TiltedLine:
    """ Represents a line tilted at a certain angle and offset from the origin"""
    def __init__(self, angle: float, offset: float):
        self.angle = angle
        self.offset = offset
        self.slope = math.tan(math.radians(angle))
        self.intercept = offset / math.sin(math.radians(angle))

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

class Layout:
    """ Calculates the layout of boards in a tilted frame"""
    def __init__(self, width, height, board_width, angle, spacing):
        self.width = width
        self.height = height
        self.board_width = board_width
        self.angle = angle
        self.spacing = spacing
        self.xmin = -width / 2
        self.xmax = width / 2
        self.ymin = -height / 2
        self.ymax = height / 2
        self.frame = ((self.xmin, self.ymin), (self.xmax, self.ymin), (self.xmax, self.ymax), (self.xmin, self.ymax))
        self.offset_step = board_width / math.sin(angle) + spacing / math.sin(angle)
        self.delta_x = width / 2 / math.tan(angle)
        self.board_x_half_width = board_width / math.sin(angle) / 2
        self.boards: list[Board] = []

    def calculate(self) -> list[Board] | None:
        offset = 0
        self.boards.append(self._try_create_board(0))
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

class Renderer:
    """ Renders the layout using Excalidraw"""
    def __init__(self, boards: list[Board]) -> None:
        self.boards = boards

    def render(self, basename = "layout.excalidraw"):
        xd = DiagramBuilder()
        for board in self.boards:
            transformed_board = [(x, -y) for (x, y) in board] # Invert Y axis for Excalidraw

            xd.line().sloppiness('architect').roundness('sharp').points(transformed_board).close().color("#000000").thickness('thin')

        xd.save(basename)


if __name__ == "__main__":
    layout = Layout(600, 400, 140, 45, 4)
    boards = layout.calculate()
    
    renderer = Renderer(boards)
    renderer.render()
    

