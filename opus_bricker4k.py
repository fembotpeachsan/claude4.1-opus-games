import pygame
import sys
import random
import numpy as np

# Initialize Pygame
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Constants
WIDTH = 600
HEIGHT = 400
FPS = 60

# Colors (Atari palette)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
PURPLE = (128, 0, 128)

# Game settings
PADDLE_WIDTH = 80
PADDLE_HEIGHT = 10
BALL_SIZE = 8
BRICK_WIDTH = 58
BRICK_HEIGHT = 20
BRICK_ROWS = 6
BRICK_COLS = 10
PADDLE_SPEED = 8
BALL_SPEED = 4

class SoundGenerator:
    def __init__(self):
        self.sample_rate = 22050
        
    def create_beep(self, frequency, duration=50):
        """Create a retro beep sound"""
        samples = int(self.sample_rate * duration / 1000)
        waves = np.array([int(16000 * np.sin(2 * np.pi * frequency * x / self.sample_rate)) 
                         for x in range(samples)])
        
        # Add some PS1-style crunch
        waves = waves + np.random.randint(-1000, 1000, samples)
        
        # Stereo sound
        stereo_waves = np.array([[w, w] for w in waves], dtype=np.int16)
        
        sound = pygame.sndarray.make_sound(stereo_waves)
        sound.set_volume(0.3)
        return sound
    
    def create_explosion(self):
        """Create a noise burst for losing ball"""
        samples = int(self.sample_rate * 0.2)
        noise = np.random.randint(-20000, 20000, samples)
        
        # Envelope to fade out
        envelope = np.linspace(1, 0, samples)
        waves = (noise * envelope).astype(np.int16)
        
        stereo_waves = np.array([[w, w] for w in waves], dtype=np.int16)
        sound = pygame.sndarray.make_sound(stereo_waves)
        sound.set_volume(0.3)
        return sound
    
    def create_powerup(self):
        """Create a rising tone for winning"""
        samples = int(self.sample_rate * 0.5)
        frequency = np.linspace(200, 800, samples)
        waves = np.array([int(10000 * np.sin(2 * np.pi * f * i / self.sample_rate)) 
                          for i, f in enumerate(frequency)])
        
        stereo_waves = np.array([[w, w] for w in waves], dtype=np.int16)
        sound = pygame.sndarray.make_sound(stereo_waves)
        sound.set_volume(0.3)
        return sound

# Create sound generator
sound_gen = SoundGenerator()

# Pre-generate sounds
sounds = {
    'paddle': sound_gen.create_beep(400, 30),
    'wall': sound_gen.create_beep(200, 20),
    'brick_high': sound_gen.create_beep(800, 40),
    'brick_mid': sound_gen.create_beep(500, 40),
    'brick_low': sound_gen.create_beep(300, 40),
    'lose': sound_gen.create_explosion(),
    'win': sound_gen.create_powerup()
}

class Ball:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.dx = random.choice([-BALL_SPEED, BALL_SPEED])
        self.dy = BALL_SPEED
        self.speed_multiplier = 1.0
    
    def update(self):
        self.x += self.dx * self.speed_multiplier
        self.y += self.dy * self.speed_multiplier
        
        # Wall collision
        if self.x <= BALL_SIZE or self.x >= WIDTH - BALL_SIZE:
            self.dx = -self.dx
            sounds['wall'].play()
        
        if self.y <= BALL_SIZE:
            self.dy = -self.dy
            sounds['wall'].play()
    
    def draw(self, screen):
        pygame.draw.rect(screen, WHITE, 
                        (self.x - BALL_SIZE//2, self.y - BALL_SIZE//2, 
                         BALL_SIZE, BALL_SIZE))

class Paddle:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT - 30
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
    
    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT] and self.x > self.width // 2:
            self.x -= PADDLE_SPEED
        if keys[pygame.K_RIGHT] and self.x < WIDTH - self.width // 2:
            self.x += PADDLE_SPEED
    
    def draw(self, screen):
        pygame.draw.rect(screen, WHITE,
                        (self.x - self.width//2, self.y - self.height//2,
                         self.width, self.height))

class Brick:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.width = BRICK_WIDTH
        self.height = BRICK_HEIGHT
        self.color = color
        self.alive = True
    
    def draw(self, screen):
        if self.alive:
            pygame.draw.rect(screen, self.color,
                           (self.x, self.y, self.width, self.height))
            pygame.draw.rect(screen, BLACK,
                           (self.x, self.y, self.width, self.height), 1)

def create_bricks():
    bricks = []
    colors = [RED, RED, ORANGE, ORANGE, YELLOW, YELLOW, GREEN, GREEN, BLUE, BLUE]
    
    for row in range(BRICK_ROWS):
        for col in range(BRICK_COLS):
            x = col * (BRICK_WIDTH + 2) + 5
            y = row * (BRICK_HEIGHT + 2) + 50
            color = colors[row] if row < len(colors) else PURPLE
            bricks.append(Brick(x, y, color))
    
    return bricks

def check_collision(ball, paddle):
    if (ball.y + BALL_SIZE//2 >= paddle.y - paddle.height//2 and
        ball.y - BALL_SIZE//2 <= paddle.y + paddle.height//2 and
        ball.x >= paddle.x - paddle.width//2 and
        ball.x <= paddle.x + paddle.width//2):
        
        # Calculate hit position for angle
        hit_pos = (ball.x - paddle.x) / (paddle.width / 2)
        ball.dx = BALL_SPEED * hit_pos
        ball.dy = -abs(ball.dy)
        
        # Speed up slightly each paddle hit
        ball.speed_multiplier = min(ball.speed_multiplier + 0.02, 2.0)
        sounds['paddle'].play()
        return True
    return False

def check_brick_collision(ball, bricks):
    for brick in bricks:
        if brick.alive:
            if (ball.x + BALL_SIZE//2 >= brick.x and
                ball.x - BALL_SIZE//2 <= brick.x + brick.width and
                ball.y + BALL_SIZE//2 >= brick.y and
                ball.y - BALL_SIZE//2 <= brick.y + brick.height):
                
                brick.alive = False
                ball.dy = -ball.dy
                
                # Different pitch for different colored bricks
                if brick.color == RED:
                    sounds['brick_high'].play()
                    return 7
                elif brick.color == ORANGE:
                    sounds['brick_high'].play()
                    return 5
                elif brick.color == YELLOW:
                    sounds['brick_mid'].play()
                    return 3
                elif brick.color == GREEN:
                    sounds['brick_mid'].play()
                    return 2
                else:
                    sounds['brick_low'].play()
                    return 1
    return 0

def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("BREAKOUT")
    clock = pygame.time.Clock()
    
    # Game objects
    ball = Ball()
    paddle = Paddle()
    bricks = create_bricks()
    
    # Game state
    score = 0
    lives = 3
    game_over = False
    game_won = False
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)
    
    running = True
    while running:
        dt = clock.tick(FPS)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE and (game_over or game_won):
                    # Reset game
                    ball.reset()
                    bricks = create_bricks()
                    score = 0
                    lives = 3
                    game_over = False
                    game_won = False
        
        if not game_over and not game_won:
            # Update
            ball.update()
            paddle.update()
            
            # Check collisions
            check_collision(ball, paddle)
            points = check_brick_collision(ball, bricks)
            score += points
            
            # Check if ball went off bottom
            if ball.y > HEIGHT:
                lives -= 1
                sounds['lose'].play()
                if lives <= 0:
                    game_over = True
                else:
                    ball.reset()
            
            # Check win condition
            if all(not brick.alive for brick in bricks):
                game_won = True
                sounds['win'].play()
        
        # Draw
        screen.fill(BLACK)
        
        # Draw game objects
        ball.draw(screen)
        paddle.draw(screen)
        for brick in bricks:
            brick.draw(screen)
        
        # Draw UI
        score_text = font.render(f"{score:04d}", True, WHITE)
        screen.blit(score_text, (10, 10))
        
        lives_text = small_font.render(f"BALLS: {lives}", True, WHITE)
        screen.blit(lives_text, (WIDTH - 100, 10))
        
        if game_over:
            game_over_text = font.render("GAME OVER", True, RED)
            restart_text = small_font.render("PRESS SPACE TO PLAY AGAIN", True, WHITE)
            screen.blit(game_over_text, 
                       (WIDTH//2 - game_over_text.get_width()//2, HEIGHT//2 - 20))
            screen.blit(restart_text,
                       (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 20))
        
        if game_won:
            win_text = font.render("YOU WIN!", True, GREEN)
            restart_text = small_font.render("PRESS SPACE TO PLAY AGAIN", True, WHITE)
            screen.blit(win_text,
                       (WIDTH//2 - win_text.get_width()//2, HEIGHT//2 - 20))
            screen.blit(restart_text,
                       (WIDTH//2 - restart_text.get_width()//2, HEIGHT//2 + 20))
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
