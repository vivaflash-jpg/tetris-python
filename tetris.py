import tkinter as tk
import random

COLS, ROWS = 10, 20
BLOCK = 32  # 블록 한 칸의 픽셀 크기
WIDTH  = COLS * BLOCK
HEIGHT = ROWS * BLOCK
SIDE_W = 160

COLORS = [
    None,
    '#00f0f0',  # I
    '#f0a000',  # O
    '#a000f0',  # T
    '#00f000',  # S
    '#f00000',  # Z
    '#0000f0',  # J
    '#f0f000',  # L
]

SHAPES = [
    None,
    [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]],  # I
    [[2,2],[2,2]],                                # O
    [[0,3,0],[3,3,3],[0,0,0]],                    # T
    [[0,4,4],[4,4,0],[0,0,0]],                    # S
    [[5,5,0],[0,5,5],[0,0,0]],                    # Z
    [[6,0,0],[6,6,6],[0,0,0]],                    # J
    [[0,0,7],[7,7,7],[0,0,0]],                    # L
]

SCORE_TABLE = [0, 100, 300, 500, 800]
BASE_SPEED  = 800
MAX_LIVES   = 3


def rotate(shape):
    return [list(row) for row in zip(*shape[::-1])]


class Tetris:
    def __init__(self, root):
        self.root = root
        root.title('테트리스')
        root.resizable(False, False)
        root.configure(bg='#1a1a2e')

        # ── layout ──────────────────────────────────────────────────
        frame = tk.Frame(root, bg='#1a1a2e')
        frame.pack(padx=16, pady=16)

        self.canvas = tk.Canvas(
            frame, width=WIDTH, height=HEIGHT,
            bg='#0d0d1a', highlightthickness=2, highlightbackground='#e94560'
        )
        self.canvas.grid(row=0, column=0)

        side = tk.Frame(frame, bg='#1a1a2e', width=SIDE_W)
        side.grid(row=0, column=1, padx=(16, 0), sticky='n')
        side.grid_propagate(False)

        def panel(parent, title):
            f = tk.Frame(parent, bg='#16213e', bd=0, highlightthickness=1,
                         highlightbackground='#0f3460')
            f.pack(fill='x', pady=(0, 10))
            tk.Label(f, text=title, bg='#16213e', fg='#e94560',
                     font=('Courier New', 9, 'bold')).pack(anchor='w', padx=10, pady=(8,0))
            val = tk.Label(f, text='0', bg='#16213e', fg='#ffffff',
                           font=('Courier New', 22, 'bold'))
            val.pack(anchor='w', padx=10, pady=(0, 8))
            return val

        self.score_lbl = panel(side, 'SCORE')
        self.level_lbl = panel(side, 'LEVEL')
        self.lines_lbl = panel(side, 'LINES')
        self.lives_lbl = panel(side, 'LIVES')

        # next piece preview
        nf = tk.Frame(side, bg='#16213e', highlightthickness=1,
                      highlightbackground='#0f3460')
        nf.pack(fill='x', pady=(0, 10))
        tk.Label(nf, text='NEXT', bg='#16213e', fg='#e94560',
                 font=('Courier New', 9, 'bold')).pack(anchor='w', padx=10, pady=(8,0))
        self.next_canvas = tk.Canvas(nf, width=SIDE_W-20, height=80,
                                     bg='#0d0d1a', highlightthickness=0)
        self.next_canvas.pack(padx=10, pady=(4, 10))

        # controls
        cf = tk.Frame(side, bg='#16213e', highlightthickness=1,
                      highlightbackground='#0f3460')
        cf.pack(fill='x')
        ctrl_text = (
            '← →   이동\n'
            '↑      회전\n'
            '↓      빠르게\n'
            'Space 즉시낙하\n'
            'P      일시정지'
        )
        tk.Label(cf, text=ctrl_text, bg='#16213e', fg='#888888',
                 font=('Courier New', 10), justify='left').pack(padx=10, pady=10)

        # ── overlay message ──────────────────────────────────────────
        self.overlay = tk.Frame(self.canvas, bg='#0d0d1a')
        self.ov_title = tk.Label(self.overlay, text='테트리스', fg='#e94560',
                                 bg='#0d0d1a', font=('Courier New', 28, 'bold'))
        self.ov_title.pack(pady=(20, 6))
        self.ov_body = tk.Label(self.overlay,
                                text='방향키로 이동  ↑ 회전  Space 즉시낙하',
                                fg='#888888', bg='#0d0d1a', font=('Courier New', 10))
        self.ov_body.pack()
        self.ov_btn = tk.Button(self.overlay, text='시작', command=self.start,
                                bg='#e94560', fg='white', font=('Courier New', 13, 'bold'),
                                relief='flat', padx=20, pady=6, cursor='hand2',
                                activebackground='#c73652', activeforeground='white')
        self.ov_btn.pack(pady=16)
        self.overlay.place(relx=0.5, rely=0.5, anchor='center')

        # ── key bindings ─────────────────────────────────────────────
        root.bind('<Left>',  lambda e: self.move(-1))
        root.bind('<Right>', lambda e: self.move(1))
        root.bind('<Down>',  lambda e: self.soft_drop())
        root.bind('<Up>',    lambda e: self.try_rotate())
        root.bind('<space>', lambda e: self.hard_drop())
        root.bind('<p>',     lambda e: self.toggle_pause())
        root.bind('<P>',     lambda e: self.toggle_pause())

        self.running = False
        self._after_id = None

    # ── game state ───────────────────────────────────────────────────

    def start(self):
        self.overlay.place_forget()
        self.root.focus_set()
        self.board  = [[0]*COLS for _ in range(ROWS)]
        self.score  = 0
        self.level  = 1
        self.lines  = 0
        self.lives  = MAX_LIVES
        self.paused = False
        self.running = True
        self.speed  = BASE_SPEED
        self.piece  = self._new_piece()
        self.next   = self._new_piece()
        self._update_ui()
        self._draw_next()
        if self._after_id:
            self.root.after_cancel(self._after_id)
        self._tick()

    def _new_piece(self):
        pid = random.randint(1, 7)
        shape = [row[:] for row in SHAPES[pid]]
        x = COLS // 2 - len(shape[0]) // 2
        return {'id': pid, 'shape': shape, 'x': x, 'y': 0}

    # ── collision / movement ─────────────────────────────────────────

    def _collides(self, shape, ox, oy):
        for r, row in enumerate(shape):
            for c, v in enumerate(row):
                if not v:
                    continue
                nx, ny = ox + c, oy + r
                if nx < 0 or nx >= COLS or ny >= ROWS:
                    return True
                if ny >= 0 and self.board[ny][nx]:
                    return True
        return False

    def move(self, dx):
        if not self.running or self.paused:
            return
        p = self.piece
        if not self._collides(p['shape'], p['x'] + dx, p['y']):
            p['x'] += dx
        self._draw()

    def soft_drop(self):
        if not self.running or self.paused:
            return
        p = self.piece
        if not self._collides(p['shape'], p['x'], p['y'] + 1):
            p['y'] += 1
        else:
            self._lock()
        self._draw()

    def hard_drop(self):
        if not self.running or self.paused:
            return
        p = self.piece
        while not self._collides(p['shape'], p['x'], p['y'] + 1):
            p['y'] += 1
        self._lock()
        self._draw()

    def try_rotate(self):
        if not self.running or self.paused:
            return
        p = self.piece
        rot = rotate(p['shape'])
        # wall kick: try 0, +1, -1, +2, -2
        for dx in (0, 1, -1, 2, -2):
            if not self._collides(rot, p['x'] + dx, p['y']):
                p['shape'] = rot
                p['x'] += dx
                break
        self._draw()

    def toggle_pause(self):
        if not self.running:
            return
        self.paused = not self.paused
        if not self.paused:
            self._tick()

    # ── lock & line clear ────────────────────────────────────────────

    def _lock(self):
        p = self.piece
        for r, row in enumerate(p['shape']):
            for c, v in enumerate(row):
                if v and p['y'] + r >= 0:
                    self.board[p['y'] + r][p['x'] + c] = v
        self._clear_lines()
        self.piece = self.next
        self.next  = self._new_piece()
        self._draw_next()
        if self._collides(self.piece['shape'], self.piece['x'], self.piece['y']):
            self._lose_life()

    def _clear_lines(self):
        cleared = 0
        r = ROWS - 1
        while r >= 0:
            if all(self.board[r]):
                del self.board[r]
                self.board.insert(0, [0] * COLS)
                cleared += 1
            else:
                r -= 1
        if cleared:
            self.score += SCORE_TABLE[min(cleared, 4)] * self.level
            self.lines += cleared
            self.level  = self.lines // 10 + 1
            self.speed  = max(80, BASE_SPEED - (self.level - 1) * 80)
            self._update_ui()

    def _lose_life(self):
        self.lives = max(0, self.lives - 1)
        self._update_ui()
        if self.lives <= 0:
            self._game_over()
            return
        # 목숨이 남아 있으면 보드만 초기화하고 재개
        self.running = False
        if self._after_id:
            self.root.after_cancel(self._after_id)
        self.ov_title.config(text=f'목숨 -1 !  남은 목숨: {self.lives}')
        self.ov_body.config(text=f'현재 점수: {self.score}')
        self.ov_btn.config(text='계속하기', command=self._resume_after_life_lost)
        self.overlay.place(relx=0.5, rely=0.5, anchor='center')

    def _resume_after_life_lost(self):
        if self.running:
            return
        self.overlay.place_forget()
        self.root.focus_set()
        self.board  = [[0]*COLS for _ in range(ROWS)]
        self.speed  = max(80, BASE_SPEED - (self.level - 1) * 80)
        self.paused = False
        self.running = True
        self.piece  = self._new_piece()
        self.next   = self._new_piece()
        self._draw_next()
        self.ov_btn.config(command=self.start)
        self._tick()

    def _game_over(self):
        self.running = False
        if self._after_id:
            self.root.after_cancel(self._after_id)
        self.ov_title.config(text='GAME OVER')
        self.ov_body.config(text=f'최종 점수:  {self.score}')
        self.ov_btn.config(text='다시 시작', command=self.start)
        self.overlay.place(relx=0.5, rely=0.5, anchor='center')

    # ── tick ─────────────────────────────────────────────────────────

    def _tick(self):
        if not self.running or self.paused:
            return
        p = self.piece
        if not self._collides(p['shape'], p['x'], p['y'] + 1):
            p['y'] += 1
        else:
            self._lock()
        if not self.running:
            return
        self._draw()
        self._after_id = self.root.after(self.speed, self._tick)

    # ── drawing ──────────────────────────────────────────────────────

    def _ghost_y(self):
        p = self.piece
        dy = 0
        while not self._collides(p['shape'], p['x'], p['y'] + dy + 1):
            dy += 1
        return p['y'] + dy

    def _draw_block(self, cvs, bx, by, color, size=BLOCK, alpha_tag=None):
        x1, y1 = bx * size + 1, by * size + 1
        x2, y2 = x1 + size - 2, y1 + size - 2
        tag = alpha_tag or ()
        cvs.create_rectangle(x1, y1, x2, y2, fill=color, outline='', tags=tag)
        cvs.create_line(x1, y1, x2, y1, fill='white', tags=tag)
        cvs.create_line(x1, y1, x1, y2, fill='white', tags=tag)

    def _draw(self):
        c = self.canvas
        c.delete('all')

        # grid
        for r in range(ROWS + 1):
            c.create_line(0, r*BLOCK, WIDTH, r*BLOCK, fill='#1a1a2e')
        for col in range(COLS + 1):
            c.create_line(col*BLOCK, 0, col*BLOCK, HEIGHT, fill='#1a1a2e')

        # board
        for r, row in enumerate(self.board):
            for col, v in enumerate(row):
                if v:
                    self._draw_block(c, col, r, COLORS[v])

        # ghost
        gy = self._ghost_y()
        p = self.piece
        if gy != p['y']:
            for r, row in enumerate(p['shape']):
                for col, v in enumerate(row):
                    if v:
                        x1 = (p['x']+col)*BLOCK+2
                        y1 = (gy+r)*BLOCK+2
                        c.create_rectangle(x1, y1, x1+BLOCK-4, y1+BLOCK-4,
                                           fill='', outline=COLORS[v],
                                           dash=(3,3))

        # current piece
        for r, row in enumerate(p['shape']):
            for col, v in enumerate(row):
                if v:
                    self._draw_block(c, p['x']+col, p['y']+r, COLORS[v])

        # pause text
        if self.paused:
            c.create_rectangle(0, HEIGHT//2-30, WIDTH, HEIGHT//2+30,
                                fill='#000000cc', outline='')
            c.create_text(WIDTH//2, HEIGHT//2, text='일 시 정 지',
                          fill='#e94560', font=('Courier New', 20, 'bold'))

    def _draw_next(self):
        nc = self.next_canvas
        nc.delete('all')
        shape = self.next['shape']
        pid   = self.next['id']
        bs = 20
        rows, cols = len(shape), len(shape[0])
        ox = (int(nc['width']) - cols * bs) // 2
        oy = (int(nc['height']) - rows * bs) // 2
        for r, row in enumerate(shape):
            for col, v in enumerate(row):
                if v:
                    x1 = ox + col*bs + 1
                    y1 = oy + r*bs + 1
                    nc.create_rectangle(x1, y1, x1+bs-2, y1+bs-2,
                                        fill=COLORS[pid], outline='')

    def _update_ui(self):
        self.score_lbl.config(text=str(self.score))
        self.level_lbl.config(text=str(self.level))
        self.lines_lbl.config(text=str(self.lines))
        self.lives_lbl.config(text='♥ ' * self.lives if self.lives > 0 else '×')


if __name__ == '__main__':
    root = tk.Tk()
    Tetris(root)
    root.mainloop()
