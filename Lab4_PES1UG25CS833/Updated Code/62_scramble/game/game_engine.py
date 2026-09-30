import random
import pygame
from game.text_box import TextBox
 
class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        self.words = ["PYTHON", "PYGAME", "PLANET", "ROCKET", "GALAXY", "STREAM", "PUZZLE", "ALGORITHM"]
        self.secret_word = ""
        self.scrambled_word = ""
        self.revealed_positions = set()
        self.round_duration_seconds = 20
        self.time_remaining = self.round_duration_seconds
        self.timer_last_update = 0
        self.is_time_up = False
        self.timeout_started_at = None
        self.timeout_display_duration_ms = 1500
        self.tile_size = 48
        self.tile_gap = 8
        self.tile_y = 152
        self.tile_order = []
        self.tile_order_changed = False
        self.selected_tile_index = None
        self.dragging_tile_index = None
        self.drag_start_position = None
        self.drag_position = None
        self.drag_moved = False

        self.score = 0
        self.feedback_msg = "Unscramble the letters above!"
        self.feedback_color = (210, 215, 225)

        self.input_box = TextBox(width // 2 - 130, 245, 160, 46)
        self.submit_btn = pygame.Rect(width // 2 + 45, 245, 95, 46)
        self.hint_btn = pygame.Rect(width // 2 + 150, 245, 95, 46)

        self.font_title = pygame.font.SysFont(None, 40)
        self.font_word = pygame.font.SysFont(None, 52)
        self.font_msg = pygame.font.SysFont(None, 26)
        self.font_btn = pygame.font.SysFont(None, 24)

        self.next_round()

    def scramble_string(self, word):
        letters = list(word)
        while True:
            random.shuffle(letters)
            shuffled = "".join(letters)
            if shuffled != word or len(word) <= 1:
                return shuffled

    def next_round(self):
        self.secret_word = random.choice(self.words)
        self.scrambled_word = self.scramble_string(self.secret_word)
        self.revealed_positions.clear()
        self._reset_tile_state()
        self.time_remaining = self.round_duration_seconds
        self.timer_last_update = pygame.time.get_ticks()
        self.is_time_up = False
        self.timeout_started_at = None
        self.input_box.clear()

    def _reset_tile_state(self):
        self.tile_order = list(self.scrambled_word)
        self.tile_order_changed = False
        self.selected_tile_index = None
        self.dragging_tile_index = None
        self.drag_start_position = None
        self.drag_position = None
        self.drag_moved = False

    def _get_tile_rects(self):
        count = len(self.tile_order)
        total_width = count * self.tile_size + max(0, count - 1) * self.tile_gap
        start_x = (self.width - total_width) // 2
        return [
            pygame.Rect(
                start_x + index * (self.tile_size + self.tile_gap),
                self.tile_y,
                self.tile_size,
                self.tile_size,
            )
            for index in range(count)
        ]

    def _tile_index_at(self, position):
        for index, tile_rect in enumerate(self._get_tile_rects()):
            if tile_rect.collidepoint(position):
                return index
        return None

    def _handle_tile_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            tile_index = self._tile_index_at(event.pos)
            if tile_index is not None:
                self.dragging_tile_index = tile_index
                self.drag_start_position = event.pos
                self.drag_position = event.pos
                self.drag_moved = False
                return True

        if event.type == pygame.MOUSEMOTION and self.dragging_tile_index is not None:
            self.drag_position = event.pos
            dx = event.pos[0] - self.drag_start_position[0]
            dy = event.pos[1] - self.drag_start_position[1]
            if dx * dx + dy * dy >= 16:
                self.drag_moved = True
            return True

        if (
            event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
            and self.dragging_tile_index is not None
        ):
            tile_index = self.dragging_tile_index
            if self.drag_moved:
                target_index = self._tile_index_at(event.pos)
                if target_index is not None and target_index != tile_index:
                    self.tile_order[tile_index], self.tile_order[target_index] = (
                        self.tile_order[target_index],
                        self.tile_order[tile_index],
                    )
                    self.tile_order_changed = self.tile_order != list(self.scrambled_word)
                self.selected_tile_index = None
            elif self.selected_tile_index is None:
                self.selected_tile_index = tile_index
            elif self.selected_tile_index == tile_index:
                self.selected_tile_index = None
            else:
                self.tile_order[self.selected_tile_index], self.tile_order[tile_index] = (
                    self.tile_order[tile_index],
                    self.tile_order[self.selected_tile_index],
                )
                self.tile_order_changed = self.tile_order != list(self.scrambled_word)
                self.selected_tile_index = None

            self.dragging_tile_index = None
            self.drag_start_position = None
            self.drag_position = None
            self.drag_moved = False
            return True

        return False

    def _draw_tile(self, screen, letter, rect, selected=False):
        fill_color = (70, 115, 175) if selected else (48, 67, 91)
        border_color = (255, 220, 120) if selected else (150, 190, 225)
        pygame.draw.rect(screen, fill_color, rect, border_radius=6)
        pygame.draw.rect(screen, border_color, rect, width=2, border_radius=6)
        letter_surf = self.font_word.render(letter, True, (245, 245, 250))
        screen.blit(letter_surf, letter_surf.get_rect(center=rect.center))

    def reveal_hint(self):
        if self.is_time_up:
            return

        unrevealed_positions = [
            index for index in range(len(self.secret_word))
            if index not in self.revealed_positions
        ]
        if not unrevealed_positions:
            self.feedback_msg = "All letters have been revealed."
            self.feedback_color = (240, 170, 50)
            return

        self.revealed_positions.add(unrevealed_positions[0])
        self.score = max(0, self.score - 1)
        self.feedback_msg = "HINT: one letter revealed (-1 point)."
        self.feedback_color = (240, 170, 50)

    def submit_guess(self):
        if self.is_time_up:
            return

        typed_guess = self.input_box.text.strip().upper()
        if typed_guess:
            guess = typed_guess
        elif self.tile_order_changed:
            guess = "".join(self.tile_order)
        else:
            guess = ""

        if not guess:
            self.feedback_msg = "Type a word before submitting!"
            self.feedback_color = (240, 170, 50)
            return

        is_correct = (guess == self.secret_word)

        if is_correct:
            self.score += 1
            self.feedback_msg = f"CORRECT! '{self.secret_word}' is right."
            self.feedback_color = (80, 230, 110)
            self.next_round()
        else:
            self.feedback_msg = "WRONG GUESS! Try again."
            self.feedback_color = (240, 80, 80)
            self.input_box.clear()

    def handle_event(self, event):
        self.update()
        if self.is_time_up:
            return

        self.input_box.handle_event(event)
        if self._handle_tile_event(event):
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.submit_guess()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.submit_btn.collidepoint(event.pos):
                self.submit_guess()
            elif self.hint_btn.collidepoint(event.pos):
                self.reveal_hint()

    def update(self):
        now = pygame.time.get_ticks()
        if self.is_time_up:
            if now - self.timeout_started_at >= self.timeout_display_duration_ms:
                self.next_round()
            return

        elapsed_seconds = (now - self.timer_last_update) // 1000
        if elapsed_seconds <= 0:
            return

        self.time_remaining = max(0, self.time_remaining - elapsed_seconds)
        self.timer_last_update += elapsed_seconds * 1000
        if self.time_remaining == 0:
            self.is_time_up = True
            self.timeout_started_at = now
            self._reset_tile_state()
            self.feedback_msg = "TIME'S UP!"
            self.feedback_color = (240, 80, 80)

    def render(self, screen):
        screen.fill((26, 30, 38))

        title_surf = self.font_title.render("Word Scramble Arena", True, (245, 245, 245))
        screen.blit(title_surf, (self.width // 2 - title_surf.get_width() // 2, 25))

        score_surf = self.font_msg.render(f"Score: {self.score}", True, (255, 220, 80))
        screen.blit(score_surf, (self.width // 2 - score_surf.get_width() // 2, 70))

        timer_color = (240, 80, 80) if self.time_remaining <= 5 else (255, 220, 120)
        timer_surf = self.font_msg.render(f"Time: {self.time_remaining}s", True, timer_color)
        screen.blit(timer_surf, (self.width // 2 - timer_surf.get_width() // 2, 100))

        if self.is_time_up:
            revealed_word = "  ".join(self.secret_word)
            answer_surf = self.font_word.render(revealed_word, True, (100, 200, 255))
            screen.blit(answer_surf, (self.width // 2 - answer_surf.get_width() // 2, 152))
        else:
            instruction_surf = self.font_msg.render(
                "Drag tiles to reorder, or click two to swap", True, (190, 200, 215)
            )
            screen.blit(
                instruction_surf,
                (self.width // 2 - instruction_surf.get_width() // 2, 124),
            )

            tile_rects = self._get_tile_rects()
            for index, (letter, tile_rect) in enumerate(zip(self.tile_order, tile_rects)):
                if index == self.dragging_tile_index and self.drag_moved:
                    pygame.draw.rect(screen, (38, 44, 56), tile_rect, border_radius=6)
                    pygame.draw.rect(
                        screen, (110, 120, 135), tile_rect, width=2, border_radius=6
                    )
                    continue
                self._draw_tile(
                    screen,
                    letter,
                    tile_rect,
                    selected=index == self.selected_tile_index,
                )

            if self.dragging_tile_index is not None and self.drag_moved:
                dragged_rect = pygame.Rect(
                    self.drag_position[0] - self.tile_size // 2,
                    self.drag_position[1] - self.tile_size // 2,
                    self.tile_size,
                    self.tile_size,
                )
                self._draw_tile(
                    screen,
                    self.tile_order[self.dragging_tile_index],
                    dragged_rect,
                    selected=True,
                )

        if self.revealed_positions and not self.is_time_up:
            hint_pattern = "  ".join(
                letter if index in self.revealed_positions else "_"
                for index, letter in enumerate(self.secret_word)
            )
            hint_surf = self.font_msg.render(f"Hint: {hint_pattern}", True, (255, 220, 120))
            screen.blit(hint_surf, (self.width // 2 - hint_surf.get_width() // 2, 207))

        self.input_box.render(screen)

        submit_color = (100, 105, 115) if self.is_time_up else (50, 150, 85)
        pygame.draw.rect(screen, submit_color, self.submit_btn, border_radius=6)
        pygame.draw.rect(screen, (220, 220, 220), self.submit_btn, width=2, border_radius=6)
        btn_text = self.font_btn.render("SUBMIT", True, (255, 255, 255))
        screen.blit(btn_text, (self.submit_btn.centerx - btn_text.get_width() // 2, self.submit_btn.centery - btn_text.get_height() // 2))

        hint_color = (
            (100, 105, 115)
            if self.is_time_up or len(self.revealed_positions) >= len(self.secret_word)
            else (70, 115, 190)
        )
        pygame.draw.rect(screen, hint_color, self.hint_btn, border_radius=6)
        pygame.draw.rect(screen, (220, 220, 220), self.hint_btn, width=2, border_radius=6)
        hint_btn_text = self.font_btn.render("HINT", True, (255, 255, 255))
        screen.blit(hint_btn_text, (self.hint_btn.centerx - hint_btn_text.get_width() // 2, self.hint_btn.centery - hint_btn_text.get_height() // 2))

        feedback_surf = self.font_msg.render(self.feedback_msg, True, self.feedback_color)
        screen.blit(feedback_surf, (self.width // 2 - feedback_surf.get_width() // 2, 325))