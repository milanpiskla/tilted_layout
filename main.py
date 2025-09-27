from excaligen.DiagramBuilder import DiagramBuilder

import math

Point = tuple[float, float]
Board = tuple[Point, Point, Point, Point]

class Layout:
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
        self.offset_step = board_width / math.sin(angle) + spacing / math.sin(angle)
        self.delta_x = width / 2 / math.tan(angle)
        self.board_x_half_width = board_width / math.sin(angle) / 2
        self.boards: list[Board] = []

    def calculate(self):
        offset = 0
        self.boards.append(self._clamp_board(self._calc_board_for_offset(offset)))
        while True:
            offset += self.offset_step
            board = self._calc_board_for_offset(offset)
            if self._board_fits(board):
                self.boards.append(self._clamp_board(board))
                self.boards.append(self._clamp_board(self._calc_board_for_offset(-offset)))

            else:
                break

    def render(self, basename = "layout.excalidraw"):
        xd = DiagramBuilder()
        xd.rectangle().center(0, 0).size(self.width, self.height).color('green').sloppiness('architect').roudness('sharp')
        for board in self.boards:
            transformed_board = [(x, -y) for (x, y) in board] # Invert Y axis for Excalidraw
            (x0, y0) = board[0]
            transformed_board.append((x0, -y0)) # Close the loop

            xd.line().sloppiness('architect').roundness('sharp').points(transformed_board).color("#000000").thickness('thin')

        xd.save(basename)


    def _calc_board_for_offset(self, offset) -> Board:
        x0 = offset - self.delta_x - self.board_x_half_width
        y0 = self.ymin
        x1 = offset - self.delta_x + self.board_x_half_width
        y1 = self.ymin
        x2 = offset + self.delta_x + self.board_x_half_width
        y2 = self.ymax
        x3 = offset + self.delta_x - self.board_x_half_width
        y3 = self.ymax

        return ((x0, y0), (x1, y1), (x2, y2), (x3, y3))
    
    def _clamp_board(self, board: Board) -> Board:
        return board

    def _board_fits(self, board: Board) -> bool:
        for (x, y) in board:
            if x >= self.xmin and x <= self.xmax:
                return True
        return False

if __name__ == "__main__":
    layout = Layout(600, 400, 140, 45, 4)
    layout.calculate()
    layout.render()

