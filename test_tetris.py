"""
테트리스 목숨 시스템 보안/정확성 테스트

재현 대상 버그:
  BUG-1  _lose_life() 에서 lives 가 음수로 언더플로우
  BUG-2  _resume_after_life_lost() 에 재진입 가드 없어 tick 루프 이중 실행
"""

import sys
import os
from unittest.mock import MagicMock
import unittest

# tkinter 는 디스플레이가 없는 환경에서 import 자체가 실패하므로 먼저 mock
sys.modules['tkinter'] = MagicMock()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tetris  # noqa: E402  (tkinter mock 이후에 import 해야 함)

COLS      = tetris.COLS
ROWS      = tetris.ROWS
MAX_LIVES = tetris.MAX_LIVES
BASE_SPEED = tetris.BASE_SPEED


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def make_game():
    """tkinter 위젯 생성을 우회해 Tetris 인스턴스를 만든다."""
    game = tetris.Tetris.__new__(tetris.Tetris)
    game.root      = MagicMock()
    game._after_id = None
    game.running   = False
    game.paused    = False
    game.board     = [[0] * COLS for _ in range(ROWS)]
    game.score     = 0
    game.level     = 1
    game.lines     = 0
    game.lives     = MAX_LIVES
    game.speed     = BASE_SPEED

    # UI 위젯 — 모두 mock
    game.score_lbl   = MagicMock()
    game.level_lbl   = MagicMock()
    game.lines_lbl   = MagicMock()
    game.lives_lbl   = MagicMock()
    game.ov_title    = MagicMock()
    game.ov_body     = MagicMock()
    game.ov_btn      = MagicMock()
    game.overlay     = MagicMock()
    game.next_canvas = MagicMock()
    game.canvas      = MagicMock()

    # _draw_next 는 Canvas 크기를 int() 로 파싱하므로 mock 으로 대체
    game._draw_next = MagicMock()

    game.piece = tetris.Tetris._new_piece(game)
    game.next  = tetris.Tetris._new_piece(game)
    return game


# ── 목숨 시스템 테스트 ─────────────────────────────────────────────────────────

class TestLivesSystem(unittest.TestCase):

    def test_initial_lives_equal_max(self):
        """게임 시작 시 목숨은 MAX_LIVES 와 같아야 한다."""
        game = make_game()
        self.assertEqual(game.lives, MAX_LIVES)

    def test_lose_life_decrements_by_one(self):
        """_lose_life() 한 번 호출 시 lives 가 정확히 1 감소해야 한다."""
        game = make_game()
        game._game_over = MagicMock()
        before = game.lives
        game._lose_life()
        self.assertEqual(game.lives, before - 1)

    def test_lose_life_shows_continue_button(self):
        """목숨이 남아 있으면 '계속하기' 버튼이 표시돼야 한다."""
        game = make_game()
        game.lives = 2
        game._lose_life()
        btn_call = str(game.ov_btn.config.call_args)
        self.assertIn('계속하기', btn_call)

    def test_lose_last_life_calls_game_over(self):
        """마지막 목숨을 잃으면 _game_over() 가 호출돼야 한다."""
        game = make_game()
        game._game_over = MagicMock()
        game.lives = 1
        game._lose_life()
        game._game_over.assert_called_once()

    # ── BUG-1 재현: lives 언더플로우 ──────────────────────────────────────────

    def test_lives_cannot_underflow_below_zero(self):
        """
        [BUG-1] lives=0 인 상태에서 _lose_life() 를 호출해도
        lives 는 0 이상이어야 한다.
        현재 코드는 lives -= 1 로 -1 이 되므로 이 테스트가 실패한다.
        """
        game = make_game()
        game._game_over = MagicMock()
        game.lives = 0
        game._lose_life()
        self.assertGreaterEqual(
            game.lives, 0,
            f"lives 가 음수({game.lives})가 됐습니다 — 언더플로우 버그"
        )

    # ── BUG-2 재현: 이중 tick 루프 ────────────────────────────────────────────

    def test_double_resume_does_not_start_two_tick_loops(self):
        """
        [BUG-2] _resume_after_life_lost() 를 두 번 연속 호출해도
        _tick() 은 정확히 1회만 실행돼야 한다.
        현재 코드는 재진입 가드가 없어 _tick() 이 두 번 호출된다.
        """
        game = make_game()
        game._tick    = MagicMock()
        game.running  = False

        game._resume_after_life_lost()
        game._resume_after_life_lost()  # 빠른 더블클릭 시뮬레이션

        self.assertEqual(
            game._tick.call_count, 1,
            f"_tick 이 {game._tick.call_count}회 호출됐습니다 — 이중 tick 루프 버그"
        )

    # ── 정상 동작 검증 ─────────────────────────────────────────────────────────

    def test_score_preserved_after_life_loss(self):
        """목숨을 잃고 재개해도 점수는 유지돼야 한다."""
        game = make_game()
        game._tick  = MagicMock()
        game.score  = 1500
        game.lives  = 2
        game._lose_life()
        game._resume_after_life_lost()
        self.assertEqual(game.score, 1500)

    def test_board_cleared_after_resume(self):
        """재개 후 보드는 완전히 비어 있어야 한다."""
        game = make_game()
        game._tick = MagicMock()
        game.board[19][0] = 1
        game.board[10][5] = 3
        game.lives = 2
        game._lose_life()
        game._resume_after_life_lost()
        for row in game.board:
            self.assertTrue(
                all(c == 0 for c in row),
                "보드에 잔여 블록이 남아 있습니다"
            )

    def test_level_preserved_after_life_loss(self):
        """목숨을 잃고 재개해도 레벨은 유지돼야 한다."""
        game = make_game()
        game._tick = MagicMock()
        game.level = 4
        game.lives = 2
        game._lose_life()
        game._resume_after_life_lost()
        self.assertEqual(game.level, 4)

    def test_lives_display_shows_correct_hearts(self):
        """LIVES 패널은 남은 목숨 수만큼 ♥ 를 표시해야 한다."""
        game = make_game()
        game.lives = 3
        game._update_ui()
        text = game.lives_lbl.config.call_args.kwargs['text']
        self.assertEqual(text.count('♥'), 3)

    def test_lives_display_shows_x_when_zero(self):
        """목숨이 0 이면 LIVES 패널에 '×' 가 표시돼야 한다."""
        game = make_game()
        game.lives = 0
        game._update_ui()
        text = game.lives_lbl.config.call_args.kwargs['text']
        self.assertIn('×', text)


# ── 회전 정확성 테스트 ────────────────────────────────────────────────────────

class TestRotation(unittest.TestCase):

    def test_rotate_clockwise(self):
        """rotate() 는 시계 방향 90도 회전을 수행해야 한다."""
        shape    = [[1, 0], [1, 0], [1, 1]]
        expected = [[1, 1, 1], [1, 0, 0]]
        self.assertEqual(tetris.rotate(shape), expected)

    def test_four_rotations_is_identity(self):
        """4회 회전하면 원래 모양으로 돌아와야 한다."""
        shape  = [[0, 1, 0], [1, 1, 1], [0, 0, 0]]
        result = shape
        for _ in range(4):
            result = tetris.rotate(result)
        self.assertEqual(result, shape)


# ── 충돌 감지 테스트 ──────────────────────────────────────────────────────────

class TestCollision(unittest.TestCase):

    def test_collision_left_wall(self):
        game = make_game()
        self.assertTrue(game._collides([[1, 1]], -1, 0))

    def test_collision_right_wall(self):
        game = make_game()
        self.assertTrue(game._collides([[1, 1]], COLS - 1, 0))

    def test_collision_floor(self):
        game = make_game()
        self.assertTrue(game._collides([[1]], 0, ROWS))

    def test_no_collision_open_space(self):
        game = make_game()
        self.assertFalse(game._collides([[1]], 5, 5))

    def test_collision_with_existing_block(self):
        game = make_game()
        game.board[10][5] = 1
        self.assertTrue(game._collides([[1]], 5, 10))


if __name__ == '__main__':
    unittest.main(verbosity=2)
