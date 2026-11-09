"""
SKYSHOTS - a vertical sky shooter game in Python (pygame).

Install:  pip install pygame
Run:      python skyshots.py

Controls:
  Arrow keys / WASD  - move
  SPACE              - shoot (hold for auto-fire)
  P                  - pause
  R                  - restart after game over
  ESC                - quit
"""

import math
import random
import sys

import pygame

# ---------------- Settings ----------------
WIDTH, HEIGHT = 480, 720
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_TOP = (10, 14, 40)
SKY_BOTTOM = (40, 20, 70)
CYAN = (80, 220, 255)
YELLOW = (255, 220, 80)
RED = (255, 70, 70)
ORANGE = (255, 150, 40)
GREEN = (90, 255, 140)
PURPLE = (190, 110, 255)


def make_gradient(w, h, top, bottom):
    surf = pygame.Surface((w, h))
    for y in range(h):
        t = y / h
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(surf, color, (0, y), (w, y))
    return surf


# ---------------- Sprites ----------------
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((50, 50), pygame.SRCALPHA)
        # Jet body
        pygame.draw.polygon(self.image, CYAN, [(25, 0), (35, 30), (25, 25), (15, 30)])
        # Wings
        pygame.draw.polygon(self.image, (40, 150, 220), [(25, 18), (50, 38), (25, 32), (0, 38)])
        # Tail
        pygame.draw.polygon(self.image, (40, 150, 220), [(25, 35), (35, 48), (15, 48)])
        # Cockpit
        pygame.draw.ellipse(self.image, WHITE, (21, 8, 8, 12))
        self.rect = self.image.get_rect(midbottom=(WIDTH // 2, HEIGHT - 30))
        self.mask = pygame.mask.from_surface(self.image)
        self.speed = 6
        self.shoot_delay = 180  # ms
        self.last_shot = 0
        self.power = 1  # 1-3 guns
        self.invincible_until = 0

    def update(self, keys):
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])
        self.rect.x += dx * self.speed
        self.rect.y += dy * self.speed
        self.rect.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))

    def can_shoot(self, now):
        return now - self.last_shot >= self.shoot_delay

    def shoot(self, now, bullets, all_sprites):
        self.last_shot = now
        x, y = self.rect.centerx, self.rect.top
        if self.power == 1:
            shots = [(x, y, 0)]
        elif self.power == 2:
            shots = [(x - 10, y + 10, 0), (x + 10, y + 10, 0)]
        else:
            shots = [(x, y, 0), (x - 14, y + 12, -1.5), (x + 14, y + 12, 1.5)]
        for sx, sy, vx in shots:
            b = Bullet(sx, sy, vx)
            bullets.add(b)
            all_sprites.add(b)

    def is_invincible(self, now):
        return now < self.invincible_until


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx=0):
        super().__init__()
        self.image = pygame.Surface((4, 14), pygame.SRCALPHA)
        pygame.draw.rect(self.image, YELLOW, (0, 0, 4, 14), border_radius=2)
        self.rect = self.image.get_rect(midbottom=(x, y))
        self.vx = vx
        self.vy = -11

    def update(self, *_):
        self.rect.x += self.vx
        self.rect.y += self.vy
        if self.rect.bottom < 0 or not (-10 < self.rect.x < WIDTH + 10):
            self.kill()


class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, x, y, vx, vy):
        super().__init__()
        self.image = pygame.Surface((8, 8), pygame.SRCALPHA)
        pygame.draw.circle(self.image, RED, (4, 4), 4)
        pygame.draw.circle(self.image, WHITE, (4, 4), 2)
        self.rect = self.image.get_rect(center=(x, y))
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(vx, vy)

    def update(self, *_):
        self.pos += self.vel
        self.rect.center = self.pos
        if not pygame.Rect(-20, -20, WIDTH + 40, HEIGHT + 40).colliderect(self.rect):
            self.kill()


class Enemy(pygame.sprite.Sprite):
    """Three kinds: 'basic' (straight down), 'zigzag', 'tank' (slow, tough, shoots)."""

    def __init__(self, level):
        super().__init__()
        self.kind = random.choices(["basic", "zigzag", "tank"], weights=[6, 3, 1 + level // 2])[0]
        if self.kind == "basic":
            size, color, self.hp, self.points = 36, RED, 1, 10
            self.speed = random.uniform(2, 3.5) + level * 0.2
        elif self.kind == "zigzag":
            size, color, self.hp, self.points = 32, ORANGE, 2, 20
            self.speed = random.uniform(2, 3) + level * 0.15
        else:
            size, color, self.hp, self.points = 54, PURPLE, 6, 50
            self.speed = 1.2 + level * 0.08

        self.max_hp = self.hp
        self.image = pygame.Surface((size, size), pygame.SRCALPHA)
        s = size
        pygame.draw.polygon(self.image, color, [(s // 2, s), (s, s // 3), (s * 3 // 4, 0),
                                                (s // 4, 0), (0, s // 3)])
        pygame.draw.circle(self.image, BLACK, (s // 2, s // 2), s // 6)
        pygame.draw.circle(self.image, WHITE, (s // 2, s // 2), s // 10)
        self.rect = self.image.get_rect(midbottom=(random.randint(size, WIDTH - size), 0))
        self.mask = pygame.mask.from_surface(self.image)
        self.base_x = self.rect.centerx
        self.t = random.uniform(0, math.pi * 2)
        self.next_shot = pygame.time.get_ticks() + random.randint(800, 2000)

    def update(self, *_):
        self.rect.y += self.speed
        if self.kind == "zigzag":
            self.t += 0.06
            self.rect.centerx = int(self.base_x + math.sin(self.t) * 70)
            self.rect.clamp_ip(pygame.Rect(0, -100, WIDTH, HEIGHT + 200))
        if self.rect.top > HEIGHT:
            self.kill()

    def try_shoot(self, now, target, enemy_bullets, all_sprites, level):
        if self.kind == "basic" and level < 3:
            return
        if now >= self.next_shot and 0 < self.rect.bottom < HEIGHT * 0.7:
            self.next_shot = now + random.randint(1200, 2500) - level * 60
            direction = pygame.Vector2(target.rect.center) - pygame.Vector2(self.rect.center)
            if direction.length() == 0:
                return
            direction = direction.normalize() * (3.5 + level * 0.15)
            b = EnemyBullet(self.rect.centerx, self.rect.bottom, direction.x, direction.y)
            enemy_bullets.add(b)
            all_sprites.add(b)


class PowerUp(pygame.sprite.Sprite):
    def __init__(self, center):
        super().__init__()
        self.kind = random.choice(["gun", "life", "speed"])
        color = {"gun": YELLOW, "life": GREEN, "speed": CYAN}[self.kind]
        letter = {"gun": "P", "life": "+", "speed": "S"}[self.kind]
        self.image = pygame.Surface((24, 24), pygame.SRCALPHA)
        pygame.draw.circle(self.image, color, (12, 12), 12)
        font = pygame.font.SysFont("arial", 16, bold=True)
        txt = font.render(letter, True, BLACK)
        self.image.blit(txt, txt.get_rect(center=(12, 12)))
        self.rect = self.image.get_rect(center=center)

    def update(self, *_):
        self.rect.y += 2
        if self.rect.top > HEIGHT:
            self.kill()


class Particle(pygame.sprite.Sprite):
    def __init__(self, pos, color):
        super().__init__()
        self.pos = pygame.Vector2(pos)
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1, 6)
        self.vel = pygame.Vector2(math.cos(angle), math.sin(angle)) * speed
        self.life = random.randint(20, 40)
        self.color = color
        self.size = random.randint(2, 5)
        self.image = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=pos)

    def update(self, *_):
        self.pos += self.vel
        self.vel *= 0.94
        self.life -= 1
        if self.life <= 0:
            self.kill()
            return
        self.image.fill((0, 0, 0, 0))
        alpha = max(0, min(255, self.life * 7))
        pygame.draw.circle(self.image, (*self.color, alpha), (self.size, self.size), self.size)
        self.rect.center = self.pos


# ---------------- Game ----------------
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("SKYSHOTS")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.big_font = pygame.font.SysFont("arial", 56, bold=True)
        self.background = make_gradient(WIDTH, HEIGHT, SKY_TOP, SKY_BOTTOM)
        # Parallax stars: [x, y, speed, size]
        self.stars = [[random.randint(0, WIDTH), random.randint(0, HEIGHT),
                       s, s] for s in (random.choice([1, 2, 3]) for _ in range(90))]
        self.high_score = 0
        self.state = "menu"
        self.reset()

    def reset(self):
        self.all_sprites = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.enemies = pygame.sprite.Group()
        self.enemy_bullets = pygame.sprite.Group()
        self.powerups = pygame.sprite.Group()
        self.particles = pygame.sprite.Group()
        self.player = Player()
        self.score = 0
        self.lives = 3
        self.level = 1
        self.last_spawn = 0
        self.shake = 0

    # ---- helpers ----
    def explode(self, pos, color, n=25):
        for _ in range(n):
            self.particles.add(Particle(pos, color))
            self.particles.add(Particle(pos, YELLOW)) if random.random() < 0.3 else None

    def spawn_delay(self):
        return max(250, 1000 - self.level * 70)

    def hit_player(self, now):
        if self.player.is_invincible(now):
            return
        self.lives -= 1
        self.shake = 15
        self.explode(self.player.rect.center, CYAN, 40)
        self.player.power = max(1, self.player.power - 1)
        self.player.invincible_until = now + 2000
        if self.lives <= 0:
            self.high_score = max(self.high_score, self.score)
            self.state = "gameover"

    # ---- main loop ----
    def run(self):
        while True:
            self.clock.tick(FPS)
            self.handle_events()
            if self.state == "playing":
                self.update()
            self.draw()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if self.state == "menu" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    self.state = "playing"
                elif self.state == "playing" and event.key == pygame.K_p:
                    self.state = "paused"
                elif self.state == "paused" and event.key == pygame.K_p:
                    self.state = "playing"
                elif self.state == "gameover" and event.key == pygame.K_r:
                    self.reset()
                    self.state = "playing"

    def update(self):
        now = pygame.time.get_ticks()
        keys = pygame.key.get_pressed()

        self.player.update(keys)
        if keys[pygame.K_SPACE] and self.player.can_shoot(now):
            self.player.shoot(now, self.bullets, self.all_sprites)

        # Level up every 300 points
        self.level = 1 + self.score // 300

        # Spawn enemies
        if now - self.last_spawn > self.spawn_delay():
            self.last_spawn = now
            e = Enemy(self.level)
            self.enemies.add(e)
            self.all_sprites.add(e)

        self.all_sprites.update()
        self.particles.update()

        for e in self.enemies:
            e.try_shoot(now, self.player, self.enemy_bullets, self.all_sprites, self.level)

        # Player bullets vs enemies
        hits = pygame.sprite.groupcollide(self.enemies, self.bullets, False, True)
        for enemy, bullet_list in hits.items():
            enemy.hp -= len(bullet_list)
            self.explode(bullet_list[0].rect.midtop, YELLOW, 4)
            if enemy.hp <= 0:
                self.score += enemy.points
                self.explode(enemy.rect.center, ORANGE, 30)
                if random.random() < 0.12:
                    p = PowerUp(enemy.rect.center)
                    self.powerups.add(p)
                    self.all_sprites.add(p)
                enemy.kill()

        # Enemies / enemy bullets vs player
        if pygame.sprite.spritecollide(self.player, self.enemies, True, pygame.sprite.collide_mask):
            self.hit_player(now)
        if pygame.sprite.spritecollide(self.player, self.enemy_bullets, True):
            self.hit_player(now)

        # Power-ups
        for p in pygame.sprite.spritecollide(self.player, self.powerups, True):
            if p.kind == "gun":
                self.player.power = min(3, self.player.power + 1)
            elif p.kind == "life":
                self.lives = min(5, self.lives + 1)
            else:
                self.player.speed = min(10, self.player.speed + 1)
            self.score += 5

        # Scroll stars
        for star in self.stars:
            star[1] += star[2]
            if star[1] > HEIGHT:
                star[0], star[1] = random.randint(0, WIDTH), 0

        if self.shake > 0:
            self.shake -= 1

    def draw_text(self, text, font, color, center):
        surf = font.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=center))

    def draw(self):
        canvas = pygame.Surface((WIDTH, HEIGHT))
        canvas.blit(self.background, (0, 0))
        for x, y, _, size in self.stars:
            shade = 120 + size * 45
            pygame.draw.circle(canvas, (shade, shade, shade), (int(x), int(y)), size // 2 + 1)

        if self.state in ("playing", "paused", "gameover"):
            for sprite in self.all_sprites:
                canvas.blit(sprite.image, sprite.rect)
            # Tank health bars
            for e in self.enemies:
                if e.max_hp > 1:
                    w = e.rect.width
                    pygame.draw.rect(canvas, RED, (e.rect.x, e.rect.y - 6, w, 4))
                    pygame.draw.rect(canvas, GREEN, (e.rect.x, e.rect.y - 6, w * e.hp / e.max_hp, 4))
            # Player (blinks while invincible)
            now = pygame.time.get_ticks()
            if self.state != "gameover" and (not self.player.is_invincible(now) or (now // 100) % 2):
                canvas.blit(self.player.image, self.player.rect)
                # Engine flame
                flame_h = random.randint(8, 16)
                pygame.draw.polygon(canvas, ORANGE, [
                    (self.player.rect.centerx - 5, self.player.rect.bottom - 2),
                    (self.player.rect.centerx + 5, self.player.rect.bottom - 2),
                    (self.player.rect.centerx, self.player.rect.bottom + flame_h)])
            for p in self.particles:
                canvas.blit(p.image, p.rect)

        # Screen shake
        offset = (random.randint(-self.shake, self.shake), random.randint(-self.shake, self.shake)) \
            if self.shake else (0, 0)
        self.screen.fill(BLACK)
        self.screen.blit(canvas, offset)

        # HUD
        if self.state != "menu":
            self.screen.blit(self.font.render(f"Score: {self.score}", True, WHITE), (10, 10))
            self.screen.blit(self.font.render(f"Level: {self.level}", True, WHITE), (10, 36))
            for i in range(self.lives):
                x = WIDTH - 30 - i * 28
                pygame.draw.polygon(self.screen, CYAN, [(x + 10, 12), (x + 20, 32), (x, 32)])

        if self.state == "menu":
            self.draw_text("SKYSHOTS", self.big_font, CYAN, (WIDTH // 2, HEIGHT // 3))
            self.draw_text("Arrows/WASD to move, SPACE to shoot", self.font, WHITE, (WIDTH // 2, HEIGHT // 2))
            self.draw_text("Press SPACE to start", self.font, YELLOW, (WIDTH // 2, HEIGHT // 2 + 50))
            if self.high_score:
                self.draw_text(f"High score: {self.high_score}", self.font, WHITE, (WIDTH // 2, HEIGHT // 2 + 100))
        elif self.state == "paused":
            self.draw_text("PAUSED", self.big_font, WHITE, (WIDTH // 2, HEIGHT // 2))
        elif self.state == "gameover":
            self.draw_text("GAME OVER", self.big_font, RED, (WIDTH // 2, HEIGHT // 3))
            self.draw_text(f"Score: {self.score}", self.font, WHITE, (WIDTH // 2, HEIGHT // 2))
            self.draw_text(f"High score: {self.high_score}", self.font, WHITE, (WIDTH // 2, HEIGHT // 2 + 30))
            self.draw_text("Press R to play again", self.font, YELLOW, (WIDTH // 2, HEIGHT // 2 + 80))

        pygame.display.flip()


if __name__ == "__main__":
    Game().run()