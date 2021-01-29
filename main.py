import pygame
import sys
from math import atan, pi, sin, cos
import os
from ctypes import windll
from Maze_generator import generate
from client import Network
from server import Server, ServerKeys
import random
import ctypes
from time import sleep


width = windll.user32.GetSystemMetrics(0)
height = windll.user32.GetSystemMetrics(1)
print(width, height)
width, height = 1200, 800
clock = pygame.time.Clock()
fps = 120
background = pygame.Color('#E6904E')
tank_color = pygame.Color('#24C911')
turret_color = pygame.Color('#248511')
bullet_color = pygame.Color("black")
start_pos = (width // 2, height // 2)
is_host = False
player_id = 1
last_bullet_id = 0
s = None
n = None
pong = 1 / 120
pong_now = pong
data_players = []
generate_seed = None

up, left, down, right,  = pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d

running = True

pygame.init()
main_screen = pygame.display.set_mode((width, height))
# main_screen = pygame.display.set_mode((width, height), pygame.FULLSCREEN)
pygame.display.set_caption("World of Tanks 2")


def load_image(filename, colorkey=None):
    fullname = os.path.join('data', 'images', filename)
    if not os.path.isfile(fullname):
        raise ValueError(f'Can\'t find the file "{filename}"')
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


def get_font_filepath(filename):
    fullname = os.path.join('data', 'fonts', filename)
    if not os.path.isfile(fullname):
        raise ValueError(f'Can\'t find the file "{filename}"')
    return fullname


def get_clipboard_text():
    CF_TEXT = 1
    kernel32 = ctypes.windll.kernel32
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    user32 = ctypes.windll.user32
    user32.GetClipboardData.restype = ctypes.c_void_p
    user32.OpenClipboard(0)
    try:
        if user32.IsClipboardFormatAvailable(CF_TEXT):
            data = user32.GetClipboardData(CF_TEXT)
            data_locked = kernel32.GlobalLock(data)
            text = ctypes.c_char_p(data_locked)
            value = text.value
            kernel32.GlobalUnlock(data_locked)
            return value
    finally:
        user32.CloseClipboard()


class Tank(pygame.sprite.Sprite):
    main_image = load_image("TankBody.png")

    def __init__(self, pos, rotation=0.0, turret_rotation=0.0, type='main', turret_type=ServerKeys.TURRET_CLASSIC):
        if type == 'main':
            data = sprites_all, sprites_tanks
        elif type == 'other':
            data = sprites_all, sprites_tanks, sprites_other_players
        else:
            data = sprites_all, sprites_tanks
        super().__init__(*data)
        self.turret_type = turret_type
        if turret_type == ServerKeys.TURRET_CLASSIC:
            turret = TurretClassic
        elif turret_type == ServerKeys.TURRET_SHOTGUN:
            turret = TurretShotgun
        elif turret_type == ServerKeys.TURRET_MINIGUN:
            turret = TurretMinigun
        else:
            turret = TurretClassic
        self.hp_start = 100
        self.hp_now = self.hp_start
        self.destroyed = False
        self.id = player_id
        self.main_rect = self.main_image.get_rect()
        self.pos_x, self.pos_y = pos
        self.rotation = rotation
        self.image, self.rect = rot_center(self.main_image,
                                           self.main_rect,
                                           rotation - 90)
        self.turret = turret((self.pos_x + self.image.get_width() // 2,
                              self.pos_y + self.image.get_height() // 2),
                             turret_rotation)
        self.rect.x, self.rect.y = int(self.pos_x), int(self.pos_y)
        self.speed = 120 * 2
        # self.speed_sqrt = self.speed / 2**0.5
        self.rotate_speed = \
            180 / ((self.image.get_width()**2 + self.image.get_height()**2)**0.5 / self.speed) / pi
        self.mask = pygame.mask.from_surface(self.image)
        # self.image.fill(tank_color)
        self.motion = 0, 0

    def update(self, seconds, x_vector=0, y_vector=0):
        """
        :param seconds: Movement's time
        :param x_vector: Vector of X movement. 0 if no movement, else 1 or -1
        :param y_vector: Vector of Y movement. 0 if no movement, else 1 or -1
        """

        if self.destroyed:
            return

        prev_pos = self.pos_x, self.pos_y
        prev_img = self.image
        prev_rect = self.rect
        prev_rot = self.rotation
        prev_mask = self.mask

        sprties_bullets_collide = pygame.sprite.spritecollide(self, sprites_bullets, False)
        for bullet in sprties_bullets_collide:
            if pygame.sprite.collide_mask(self, bullet):
                self.hp_now -= bullet.damage
                bullet.kill()
                if self.hp_now <= 0:
                    self.destroy()
                    return False

        x_movement, y_movement = self.update_from_vectors(seconds, x_vector, y_vector)

        self.motion = x_vector, y_vector

        if collideanymask(self, sprites_walls_base) or collideanymask(self, sprites_other_players):
            self.rect = prev_rect
            self.image = prev_img
            self.pos_x, self.pos_y = prev_pos
            self.rotation = prev_rot
            self.mask = prev_mask
            bad = False

        self.update_turret()

    def update_turret(self):
        center_x, center_y = self.rect.center
        new_dot = rot_dot((self.pos_x + self.main_image.get_width() // 2,
                           self.pos_y + self.main_image.get_height() // 2),
                          (center_x, center_y),
                          self.rotation)
        # new_dot = new_dot[0], new_dot[1] - 5 * cos(self.rotation * pi / 180)
        self.turret.set_pos((self.pos_x + self.image.get_width() // 2,
                             self.pos_y + self.image.get_height() // 2))

    def make_last_movement(self, seconds):
        pass
        # self.update_from_vectors(seconds, *self.motion)

    def destroy(self):
        self.destroyed = True
        self.turret.kill()
        self.kill()

    def update_from_vectors(self, seconds, x_vector, y_vector):
        x_movement = 0
        y_movement = 0
        if x_vector:
            if y_vector == 1:
                self.rotation = (self.rotation + x_vector * seconds * self.rotate_speed) % 360
            else:
                self.rotation = (self.rotation - x_vector * seconds * self.rotate_speed) % 360
            self.image, self.rect = rot_center(self.main_image,
                                               self.main_rect,
                                               self.rotation - 90)
            self.mask = pygame.mask.from_surface(self.image)
        if y_vector:
            x_movement = y_vector * self.speed * seconds * sin((self.rotation - 90) * pi / 180)
            y_movement = y_vector * self.speed * seconds * cos((self.rotation - 90) * pi / 180)
            self.pos_x += x_movement
            self.pos_y += y_movement
        elif not x_vector:
            pass  # Может, сделать здесь дрожание танка при неподвижном состоянии?

        self.update_rect()
        return x_movement, y_movement

    def update_rect(self, pos=None):
        if pos is None:
            self.rect.x = int(self.pos_x)
            self.rect.y = int(self.pos_y)
        else:
            self.pos_x, self.pos_y = pos
            self.rect.x = int(self.pos_x)
            self.rect.y = int(self.pos_y)

    def get_info(self):
        if self.destroyed:
            return None
        info = {
            "player_id": self.id,
            "pos": (self.pos_x, self.pos_y),
            "motion": self.motion,
            "rotation": self.rotation,
            "rotation_turret": self.turret.rotation,
            "turret_type": self.turret_type
        }
        return info

    def load_info(self, info):
        if info is None:
            self.destroy()
            return
        self.id = info['player_id']
        self.update_rect(info['pos'])
        self.motion = info['motion']
        self.rotation = info['rotation']
        self.turret.set_angle(info['rotation_turret'])
        self.turret.set_pos(info['pos'])
        self.turret_type = info['turret_type']


class Turret(pygame.sprite.Sprite):
    main_image = load_image("TankTurret.png")

    def __init__(self, pos, rotation=0.0):
        # main params
        super().__init__(sprites_all, sprites_turrets)
        self.main_rect = self.main_image.get_rect()
        self.pos_x, self.pos_y = pos
        self.rotation = rotation
        self.image, self.rect = rot_center(self.main_image,
                                           self.main_rect,
                                           rotation - 90)
        self.width = self.main_image.get_width() // 2
        self.height = self.main_image.get_height() // 2
        self.set_pos()
        self.mask = pygame.mask.from_surface(self.image)
        self.reload_time = 0

        # custom settings
        self.rotate_speed = 360 * 8
        self.bullet_speed = 400
        self.shot_delay = 0.4
        self.bullet = Bullet

    def update(self, seconds, pos):
        x, y = pos
        a, b = -(y - self.pos_y), (x - self.pos_x)
        if b == 0:
            final_angle = 90 if a >= 0 else -90
        else:
            final_angle = atan(a / b) * 180 / pi
        if b < 0:
            final_angle += 180
        final_angle %= 360
        dim = 1
        if final_angle != self.rotation:
            angel = (final_angle - self.rotation) % 360
            if angel >= 180:
                dim = -1
                angel = -angel % 360
            rotate_movement = self.rotate_speed * seconds
            if angel > rotate_movement:
                self.rotation += dim * rotate_movement
            else:
                self.rotation = final_angle
            self.image, self.rect = rot_center(self.main_image,
                                               self.main_rect,
                                               self.rotation - 90)
        self.set_pos()
        self.mask = pygame.mask.from_surface(self.image)

    def set_angle(self, angle):
        if angle == self.rotation:
            return
        self.image, self.rect = rot_center(self.main_image,
                                           self.main_rect,
                                           self.rotation - 90)
        self.set_pos()
        self.mask = pygame.mask.from_surface(self.image)

    def set_pos(self, pos=None):
        if pos is not None:
            self.pos_x, self.pos_y = pos
            self.rect.center = int(self.pos_x), int(self.pos_y)
        else:
            self.rect.center = int(self.pos_x), int(self.pos_y)

    def reload(self, seconds, need_shot=False):
        self.reload_time = max(0, self.reload_time - seconds)

    def make_shot(self):
        if collideanymask(self, sprites_walls_base):
            return
        if self.reload_time > 0:
            return
        self.shot_func()
        self.reload_time = self.shot_delay

    def shot_func(self):
        angle_rad = self.rotation * pi / 180
        pos_x, pos_y = self.pos_x, self.pos_y
        pos_y -= (self.height - self.bullet.size // 2) * sin(angle_rad)
        pos_x += (self.height - self.bullet.size // 2) * cos(angle_rad)
        bullet = self.bullet((pos_x, pos_y), self.bullet_speed, self.rotation)
        create_bullet(bullet)


class TurretClassic(Turret):
    main_image = load_image("TankTurret.png")

    def __init__(self, pos, rotation=0.0):
        super().__init__(pos, rotation)
        self.rotate_speed = 360 * 8
        self.bullet_speed = 400
        self.shot_delay = 0.4
        self.bullet = BulletClassic

    def shot_func(self):
        angle_rad = self.rotation * pi / 180
        pos_x, pos_y = self.pos_x, self.pos_y
        pos_y -= (self.height - self.bullet.size // 2) * sin(angle_rad)
        pos_x += (self.height - self.bullet.size // 2) * cos(angle_rad)
        bullet = self.bullet((pos_x, pos_y), self.bullet_speed, self.rotation)
        create_bullet(bullet)


class TurretShotgun(Turret):
    main_image = load_image("ShotgunTurret.png")

    def __init__(self, pos, rotation=0.0):
        super().__init__(pos, rotation)
        self.rotate_speed = 360
        self.bullet_speed = 250
        self.shot_delay = 1.2
        self.bullets_count = 10
        self.bullet = BulletShotgun
        self.max_offset_rot = 10
        self.max_offset_pos = 5

    def shot_func(self):
        for _ in range(self.bullets_count):
            rot_now = \
                self.rotation + random.random() * self.max_offset_rot * 2 - self.max_offset_rot
            offset_x = random.random() * self.max_offset_pos * 2 - self.max_offset_pos
            offset_y = random.random() * self.max_offset_pos * 2 - self.max_offset_pos
            angle_rad = rot_now * pi / 180
            pos_x, pos_y = self.pos_x, self.pos_y
            pos_y -= (self.height) * sin(angle_rad) + offset_y
            pos_x += (self.height) * cos(angle_rad) + offset_x
            bullet = self.bullet((pos_x, pos_y), self.bullet_speed, rot_now)


class TurretMinigun(Turret):
    main_image = load_image("GatlingTurret1.png")

    def __init__(self, pos, rotation=0.0):
        super().__init__(pos, rotation)
        self.shooting_rotate_speed = 30
        self.common_rotate_speed = 270
        self.start_shooting_delay = 1
        self.start_shooting_delay_now = 0
        self.shooting_time = 7
        self.shooting_time_now = 0
        self.cooldown = 3
        self.cooldown_now = 0
        self.rotate_speed = self.common_rotate_speed
        self.bullet_speed = 500
        self.shot_delay = 0.03
        self.bullet = BulletMinigun
        self.max_offset_rot = 4
        self.max_offset_pos = 2
        self.state = 0  # 0 - prepare, 1 - shooting, 2 - cooldown

    def reload(self, seconds, need_shot=False):
        if self.state == 0:
            if need_shot:
                self.start_shooting_delay_now += seconds
                if self.start_shooting_delay_now >= self.start_shooting_delay:
                    self.start_shooting_delay_now = 0
                    self.state = (self.state + 1) % 3
                    self.rotate_speed = self.shooting_rotate_speed
                else:
                    self.rotate_speed = (self.common_rotate_speed - self.shooting_rotate_speed) * \
                                        (self.start_shooting_delay - self.start_shooting_delay_now) * \
                                        self.start_shooting_delay + self.shooting_rotate_speed
            else:
                self.start_shooting_delay_now = max(0, self.start_shooting_delay_now - seconds)
                self.shooting_time_now = max(0, self.shooting_time_now - seconds)
                self.rotate_speed = (self.common_rotate_speed - self.shooting_rotate_speed) * \
                                    (self.start_shooting_delay - self.start_shooting_delay_now) * \
                                    self.start_shooting_delay + self.shooting_rotate_speed

        elif self.state == 1:
            self.reload_time = max(0, self.reload_time - seconds)
            if need_shot:
                self.shooting_time_now += seconds
                if self.shooting_time_now >= self.shooting_time:
                    self.shooting_time_now = 0
                    self.state = (self.state + 1) % 3
                    self.rotate_speed = self.common_rotate_speed
                    self.reload_time = 0
            else:
                self.state = (self.state - 1) % 3
                self.start_shooting_delay_now = max(0, self.start_shooting_delay - seconds)
                self.rotate_speed = self.common_rotate_speed
                self.shooting_time_now = max(0, self.shooting_time_now - seconds)
        elif self.state == 2:
            self.cooldown_now += seconds
            if self.cooldown_now >= self.cooldown:
                self.cooldown_now = 0
                self.state = (self.state + 1) % 3

    def make_shot(self):
        if collideanymask(self, sprites_walls_base):
            return
        if self.state != 1 or self.reload_time > 0:
            return
        self.shot_func()
        self.reload_time = self.shot_delay

    def shot_func(self):
        rot_now = \
            self.rotation + random.random() * self.max_offset_rot * 2 - self.max_offset_rot
        offset_x = random.random() * self.max_offset_pos * 2 - self.max_offset_pos
        offset_y = random.random() * self.max_offset_pos * 2 - self.max_offset_pos
        angle_rad = rot_now * pi / 180
        pos_x, pos_y = self.pos_x, self.pos_y
        pos_y -= (self.height) * sin(angle_rad) + offset_y
        pos_x += (self.height) * cos(angle_rad) + offset_x
        bullet = self.bullet((pos_x, pos_y), self.bullet_speed, rot_now)


class Bullet(pygame.sprite.Sprite):
    size = 10
    main_image = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    pygame.draw.circle(main_image, bullet_color,
                       (main_image.get_width() // 2, main_image.get_height() // 2),
                       min(main_image.get_width() // 2, main_image.get_height() // 2))
    # main_image = pygame.transform.scale(load_image('Bullet.png'), (10, 10))

    def __init__(self, pos, speed, angle=0.0, shooted=True):
        global last_bullet_id

        self.player_id = player_id
        super().__init__(sprites_all, sprites_bullets)
        self.pos_x, self.pos_y = 0, 0
        self.speed = speed
        last_bullet_id += 1
        self.id = last_bullet_id
        self.speed_x = 0
        self.speed_y = 0
        if shooted:
            self.from_speed_and_angle(speed, angle)
        else:
            self.speed_x, self.speed_y = speed
        self.image = self.main_image
        self.rect = self.image.get_rect()
        self.set_pos(pos)
        self.last_collided = None
        self.last_motion = (1, 1)
        self.width, self.height = self.image.get_width(), self.image.get_height()
        self.collided_count = 0

        # custom settings
        self.max_collided_count = 5
        self.damage = 20
        self.type = ServerKeys.BULLET_CLASSIC

    def from_speed_and_angle(self, speed, angle):
        angle_rad = -angle * pi / 180
        self.speed_x = speed * cos(angle_rad)
        self.speed_y = speed * sin(angle_rad)

    def update(self, seconds):
        self.pos_x += self.speed_x * seconds
        self.pos_y += self.speed_y * seconds
        self.set_pos((self.pos_x, self.pos_y))
        sprite = pygame.sprite.spritecollideany(self, sprites_walls_base)
        if self.pos_x > width or self.pos_x < -self.width or \
                self.pos_y > height or self.pos_y < -self.height:
            self.kill()
            return
        # if sprite:
        #     if sprite != self.last_collided:
        #         if sprite.is_horizontal():
        #             self.speed_y *= -1
        #         else:
        #             self.speed_x *= -1
        if sprite:
            self.collided_count += 1
            if self.collided_count >= self.max_collided_count:
                self.kill()
                return
            if sprite.is_horizontal():
                if pygame.sprite.spritecollideany(self, sprites_walls_hr):
                    self.speed_x *= -1
                else:
                    self.speed_y *= -1
            else:
                if pygame.sprite.spritecollideany(self, sprites_walls_vr):
                    self.speed_y *= -1
                else:
                    self.speed_x *= -1
            self.set_pos((self.pos_x + self.speed_x * seconds * 2,
                          self.pos_y + self.speed_y * seconds * 2))
            if pygame.sprite.spritecollideany(self, sprites_walls_base) == sprite:
                self.speed_x *= -1
                self.speed_y *= -1
            self.set_pos((self.pos_x, self.pos_y))

        self.last_collided = sprite

    def set_pos(self, pos):
        self.pos_x, self.pos_y = pos
        self.rect.center = int(self.pos_x), int(self.pos_y)

    def get_info(self):
        info = {
            "player_id": self.player_id,
            "id": self.id,
            "pos": (self.pos_x, self.pos_y),
            "speed": (self.speed_x, self.speed_y),
            "type": self.type
        }
        return info

    def load_info(self, info):
        self.player_id = info['player_id']
        self.id = info['id']
        self.set_pos(info['pos'])
        self.speed_x, self.speed_y = info['speed']


class BulletClassic(Bullet):
    size = 10
    main_image = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    pygame.draw.circle(main_image, bullet_color,
                       (main_image.get_width() // 2, main_image.get_height() // 2),
                       min(main_image.get_width() // 2, main_image.get_height() // 2))

    def __init__(self, pos, speed, angle=0.0, shooted=True):
        super().__init__(pos, speed, angle, shooted=shooted)
        self.max_collided_count = 5
        self.damage = 20
        self.type = ServerKeys.BULLET_CLASSIC


class BulletShotgun(Bullet):
    size = 6
    main_image = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    pygame.draw.circle(main_image, bullet_color,
                       (main_image.get_width() // 2, main_image.get_height() // 2),
                       min(main_image.get_width() // 2, main_image.get_height() // 2))

    def __init__(self, pos, speed, angle=0.0, shooted=True):
        super().__init__(pos, speed, angle, shooted=shooted)
        self.max_collided_count = 3
        self.damage = 7
        self.type = ServerKeys.BULLET_SHOTGUN


class BulletMinigun(Bullet):
    size = 6
    main_image = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    pygame.draw.circle(main_image, bullet_color,
                       (main_image.get_width() // 2, main_image.get_height() // 2),
                       min(main_image.get_width() // 2, main_image.get_height() // 2))

    def __init__(self, pos, speed, angle=0.0, shooted=True):
        super().__init__(pos, speed, angle, shooted=shooted)
        self.max_collided_count = 1
        self.damage = 3
        self.type = ServerKeys.BULLET_MINIGUN


class Wall(pygame.sprite.Sprite):
    wall_width = 16
    wall_length = 120 + wall_width
    wall_color = pygame.Color("#983300")
    image_ver = load_image('wall_v.png')
    image_hor = load_image('wall_h.png')
    # image_hor = pygame.transform.rotate(image_ver, 90)
    # image_hor = pygame.Surface((wall_length, wall_width), pygame.SRCALPHA, 32)
    # image_ver = pygame.Surface((wall_width, wall_length), pygame.SRCALPHA, 32)
    # image_hor.fill(wall_color)
    # image_ver.fill(wall_color)

    def __init__(self, pos, horizontal=True):
        super().__init__(sprites_all, sprites_walls, sprites_walls_base)
        self.pos_x, self.pos_y = pos
        if horizontal:
            self.image = self.image_hor
        else:
            self.image = self.image_ver
        self.rect = self.image.get_rect()

        self.sprites_vr = [pygame.sprite.Sprite(sprites_all, sprites_walls_vr, sprites_walls)] * 2
        for sprite in self.sprites_vr:
            sprite.image = pygame.Surface((1, self.image.get_height()), pygame.SRCALPHA, 32)
            sprite.rect = sprite.image.get_rect()
        self.sprites_vr[0].rect.center = int(self.pos_x), int(self.pos_y - self.image.get_width() / 2)
        self.sprites_vr[1].rect.center = int(self.pos_x), int(self.pos_y + self.image.get_width() / 2)

        self.sprites_hr = [pygame.sprite.Sprite(sprites_all, sprites_walls_hr, sprites_walls)] * 2
        for sprite in self.sprites_hr:
            sprite.image = pygame.Surface((self.image.get_width(), 1), pygame.SRCALPHA, 32)
            sprite.rect = sprite.image.get_rect()
        self.sprites_hr[0].rect.center = int(self.pos_x - self.image.get_height() / 2), int(self.pos_y)
        self.sprites_hr[1].rect.center = int(self.pos_x + self.image.get_height() / 2), int(self.pos_y)

        self.rect.center = int(self.pos_x), int(self.pos_y)
        self.horizontal = horizontal

    def is_horizontal(self):
        return self.horizontal


def terminate(exit_code=0):
    pygame.quit()
    if n:
        n.stop()
    if is_host and s:
        s.stop()
    sys.exit(exit_code)


def rot_center(image, rect, angle):
    rot_image = pygame.transform.rotate(image, angle)
    rot_rect = rot_image.get_rect(center=rect.center)
    return rot_image, rot_rect


def rot_dot(dot_center, dot, angel):
    """
    rotates a *dot* relative to *dot_center* by an *angel*

    :param dot_center: main dot
    :param dot: dot to rotate
    :param angel: angel in degrees
    :return: dot after rotate
    """
    angel = angel * pi / 180
    x, y = dot_center
    x1, y1 = dot
    x1 -= x
    y1 -= y
    c = (x1**2 + y1**2)**0.5
    if x1 == 0:
        angel_start = pi / 2 if y1 > 0 else -pi / 2
    else:
        angel_start = atan(y1 / x1)
        if x1 < 0:
            angel_start += pi
    new_angel = (angel_start + angel) % (2 * pi)
    new_x1, new_y1 = cos(new_angel) * c + x, sin(new_angel) * c + y
    return new_x1, new_y1


def rotate(img, pos, angle):
    w, h = img.get_size()
    img2 = pygame.Surface((w*2, h*2), pygame.SRCALPHA)
    img2.blit(img, (w - pos[0], h - pos[1]))
    return pygame.transform.rotate(img2, angle)


def collideanymask(sprite: pygame.sprite.Sprite, group: pygame.sprite.Group):
    for sprite2 in group.sprites():
        if pygame.sprite.collide_mask(sprite, sprite2):
            return True
    return False


def get_info():
    bullets = []
    for bullet in sprites_bullets.sprites():
        if bullet.player_id == player_id:
            bullets.append(bullet.get_info())
    info = {
        'player': player.get_info(),
        'bullets': bullets
    }
    return info


sprites_all = pygame.sprite.Group()
sprites_tanks = pygame.sprite.Group()
sprites_other_players = pygame.sprite.Group()
sprites_turrets = pygame.sprite.Group()
sprites_walls = pygame.sprite.Group()
sprites_walls_hr = pygame.sprite.Group()
sprites_walls_vr = pygame.sprite.Group()
sprites_walls_base = pygame.sprite.Group()
sprites_bullets = pygame.sprite.Group()
sprites_other_bullets = pygame.sprite.Group()


class Menu:
    main_image = pygame.transform.scale(load_image('MenuArt.png'), (width, height))

    play_button_1 = pygame.transform.scale2x(load_image('Play_button1.png'))
    play_button_2 = pygame.transform.scale2x(load_image('Play_button2.png'))
    options_button_1 = pygame.transform.scale2x(load_image('Options_button1.png'))
    options_button_2 = pygame.transform.scale2x(load_image('Options_button2.png'))
    exit_button_1 = pygame.transform.scale2x(load_image('Exit_button1.png'))
    exit_button_2 = pygame.transform.scale2x(load_image('Exit_button2.png'))

    class MenuButton(pygame.sprite.Sprite):
        def __init__(self, menu, pos, image, hover_image=None, click_func=None):
            super().__init__(menu.sprites_buttons)
            self.menu = menu
            self.click_func = click_func
            self.pos_x, self.pos_y = pos
            self.main_image = image
            self.hover_image = hover_image
            self.image = image
            self.rect = self.image.get_rect()
            self.rect.x, self.rect.y = int(self.pos_x), int(self.pos_y)
            self.width = image.get_width()
            self.height = image.get_height()

        def update(self, mouse_pos):
            if self.hover_image is None:
                return False
            if self.is_collided(mouse_pos):
                self.image = self.hover_image
            else:
                self.image = self.main_image

        def check_click(self, mouse_pos):
            if self.click_func is None:
                return
            if self.is_collided(mouse_pos):
                self.click_func()
                return True
            return False

        def is_collided(self, dot):
            x, y = dot
            if (self.pos_x <= x <= self.pos_x + self.width) and \
                    (self.pos_y <= y <= self.pos_y + self.height):
                return True
            return False

    def __init__(self):
        self.sprites_buttons = pygame.sprite.Group()
        self.menu_running = True
        self.background = self.main_image
        self.buttons = [
            self.MenuButton(self, (90, 180), self.play_button_1, self.play_button_2, self.play),
            self.MenuButton(self, (80, 280), self.options_button_1, self.options_button_2),
            self.MenuButton(self, (80, 400), self.exit_button_1, self.exit_button_2, self.exit)
        ]

    def exit(self):
        terminate()

    def play(self):
        self.menu_running = False
        menu_host = MenuHost()
        menu_host.start()

    def start(self):
        main_screen.blit(self.main_image, (0, 0))
        pygame.display.flip()
        clock.tick()

        while self.menu_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    terminate()
                    self.menu_running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == pygame.BUTTON_LEFT:
                        for button in self.sprites_buttons.sprites():
                            if button.check_click(event.pos):
                                break
            seconds = clock.tick(fps) / 1000
            mouse_pos = pygame.mouse.get_pos()
            self.sprites_buttons.update(mouse_pos)
            main_screen.blit(self.main_image, (0, 0))
            self.sprites_buttons.draw(main_screen)
            pygame.display.flip()


class MenuHost:
    main_image = pygame.transform.scale2x(load_image('MenuHost/main.png'))

    connect_button_1 = pygame.transform.scale2x(load_image('MenuHost/ConnectButton1.png'))
    connect_button_2 = pygame.transform.scale2x(load_image('MenuHost/ConnectButton2.png'))
    exit_button_1 = pygame.transform.scale2x(load_image('MenuHost/ExitButton1.png'))
    exit_button_2 = pygame.transform.scale2x(load_image('MenuHost/ExitButton2.png'))
    host_button_1 = pygame.transform.scale2x(load_image('MenuHost/HostButton1.png'))
    host_button_2 = pygame.transform.scale2x(load_image('MenuHost/HostButton2.png'))
    your_box = pygame.transform.scale2x(load_image('MenuHost/YourBox.png'))
    other_box = pygame.transform.scale2x(load_image('MenuHost/OtherBox.png'))
    start_button = pygame.transform.scale2x(load_image('MenuHost/StartButton.png'))

    class MenuButton(pygame.sprite.Sprite):
        def __init__(self, menu, pos, image, click_image=None, click_func=None, actived=False):
            super().__init__(menu.sprites_buttons)
            self.menu = menu
            self.click_func = click_func
            self.pos_x, self.pos_y = pos
            self.main_image = image
            self.click_image = click_image
            self.click_time = 0.05
            self.click_time_now = 0
            self.image = image
            self.rect = self.image.get_rect()
            self.rect.x, self.rect.y = int(self.pos_x), int(self.pos_y)
            self.width = image.get_width()
            self.height = image.get_height()
            self.active = None
            self.actived = actived

        def update(self, seconds):
            if self.actived:
                if not self.active or self.click_image is None:
                    self.image = self.main_image
                else:
                    self.image = self.click_image
            elif self.click_time_now > 0:
                self.click_time_now = max(0, self.click_time_now - seconds)
                if self.click_image is not None:
                    self.image = self.click_image
            else:
                self.image = self.main_image

        def check_click(self, mouse_pos):
            if self.is_collided(mouse_pos):
                if self.actived:
                    self.active = not self.active
                else:
                    self.click_time_now = self.click_time
                if self.click_func is not None:
                    self.click_func()
                return True
            return False

        def is_collided(self, dot):
            x, y = dot
            if (self.pos_x <= x <= self.pos_x + self.width) and \
                    (self.pos_y <= y <= self.pos_y + self.height):
                return True
            return False

        def is_active(self):
            if self.actived:
                return self.active
            return None

        def set_active_state(self, is_active: bool):
            if self.active == is_active:
                return False
            self.active = is_active
            return True

    class MenuInput(pygame.sprite.Sprite):
        def __init__(self, menu, geometry, max_len=20, font_size=24, font_color=pygame.Color("#eeffcc"),
                     pl=7, only_digits=False):
            super().__init__(menu.sprites_inputs)
            self.active = False
            self.text = ""
            self.menu = menu
            self.pos_x, self.pos_y, self.width, self.height = geometry
            self.max_len = max_len
            self.font_size = font_size
            self.font_color = font_color
            self.pl = pl  # padding-left
            self.only_digits = only_digits
            self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA, 32)
            self.rect = self.image.get_rect()
            self.rect.x, self.rect.y = int(self.pos_x), int(self.pos_y)
            self.font = pygame.font.Font(get_font_filepath('visitor.ttf'), self.font_size)
            self.text_w = 0
            self.text_h = 0
            self.vert_time = 0.5
            self.vert_delay = 1 - self.vert_time
            self.vert_time_now = 1
            self.vert_delay_now = 0
            self.is_vert = False

        def get_text(self):
            return self.text

        def is_active(self):
            return self.active

        def is_collided(self, dot):
            x, y = dot
            if (self.pos_x <= x <= self.pos_x + self.width) and \
                    (self.pos_y <= y <= self.pos_y + self.height):
                return True
            return False

        def del_char(self):
            if self.text:
                self.text = self.text[:-1]

        def print_char(self, char):
            if len(self.text) < self.max_len:
                if not self.only_digits or char in "1234567890.":
                    self.text += char

        def check_click(self, mouse_pos):
            if self.is_collided(mouse_pos):
                self.active = True
                return True
            self.active = False
            return False

        def update(self, seconds):
            text_to_render = self.text
            if self.active:
                if self.vert_time_now > 0:
                    text_to_render += "|"
                    self.vert_time_now = max(0, self.vert_time_now - seconds)
                elif self.vert_delay_now > 0:
                    self.vert_delay_now = max(0, self.vert_delay_now - seconds)
                else:
                    self.vert_time_now = self.vert_time
                    self.vert_delay_now = self.vert_delay
            else:
                self.vert_time_now = 1
                self.vert_delay_now = self.vert_delay
            text = self.font.render(text_to_render, True, self.font_color)
            self.text_w = text.get_width()
            self.text_h = text.get_height()
            text_x = self.pl
            text_y = self.height // 2 - self.text_h // 2 - 1
            self.image = pygame.Surface((self.width, self.height), pygame.SRCALPHA, 32)
            self.image.blit(text, (text_x, text_y))
            # TODO: курсор

        def print_text(self, text):
            text = text.strip()
            text = text[:min(self.max_len - len(self.text), len(text))]
            good_str_all = "qwertyuiopasdfghjklzxcvbnm.1234567890-_"
            good_str_digits = "1234567890."
            good_str = good_str_digits if self.only_digits else good_str_all
            good = True
            for c in text:
                if c not in good_str:
                    good = False
                    break
            if good:
                self.text += text

    def __init__(self):
        self.sprites_buttons = pygame.sprite.Group()
        self.sprites_inputs = pygame.sprite.Group()
        self.menu_running = True
        self.background = self.main_image
        self.font = pygame.font.Font(get_font_filepath('visitor.ttf'), 28)
        self.font_color = pygame.Color("#eeffcc")
        self.buttons = [
            self.MenuButton(self, (482, 290), self.host_button_1, self.host_button_2,
                            click_func=lambda: self.set_host(True), actived=True),
            self.MenuButton(self, (640, 290), self.connect_button_1, self.connect_button_2,
                            click_func=lambda: self.set_host(False), actived=True),
            # self.MenuButton(self, (80, 400), self.exit_button_1, self.exit_button_2, click_func=self.exit),
            self.MenuButton(self, (1024, 290), self.exit_button_1, click_func=self.exit),
            self.MenuButton(self, (472, 673), self.start_button, click_func=self.start_game)
        ]
        self.inputs = [
            self.MenuInput(self, (314, 186, 234, 26), only_digits=True),
            self.MenuInput(self, (314, 224, 234, 26)),
        ]
        self.players = dict()

    def start_game(self):
        global is_host
        if not is_host:
            return False
        n.send_pickle({
            'key': ServerKeys.START_GAME,
            'player_id': player_id,
            'data': random.random()
        })

    def set_host(self, state: bool):
        global is_host, s, n, player_id

        is_host = state
        need_change1 = self.buttons[0].set_active_state(is_host)
        need_change2 = self.buttons[1].set_active_state(not is_host)
        need_change = need_change1 or need_change2
        if not need_change:
            return
        server = self.inputs[0].get_text()
        if is_host:
            if s:
                s.stop()
            s = Server(server=server)
            s.start()
        if n:
            n.stop()
        n = Network(server=server)
        player_id = n.id
        n.send_pickle({
            'key': ServerKeys.NEW_INFORMATION_LOBBY,
            'player_id': player_id,
            'data': {
                'nickname': self.inputs[1].get_text()
            }
        })
        n.start()

    def exit(self):
        global s, n

        self.menu_running = False
        if s:
            s.stop()
        if n:
            n.stop()
        menu = Menu()
        menu.start()
        # terminate()

    def print_char(self, char):
        self.text += char

    def delete_char(self):
        if self.text:
            self.text = self.text[:-1]

    def start(self):
        global pong
        main_screen.blit(self.main_image, (0, 0))
        pygame.display.flip()
        clock.tick()
        pong_now = pong

        while self.menu_running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.menu_running = False
                    terminate()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == pygame.BUTTON_LEFT:
                        for button in self.sprites_buttons.sprites():
                            if button.check_click(event.pos):
                                break
                        for input in self.sprites_inputs.sprites():
                            input.check_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    key = event.key
                    active_input = None
                    for input in self.sprites_inputs.sprites():
                        if input.is_active():
                            active_input = input
                    if active_input is not None:
                        if key == 8:  # backspace
                            active_input.del_char()
                        elif key == pygame.K_v and (pygame.KMOD_LCTRL or pygame.KMOD_RCTRL or pygame.KMOD_CTRL):
                            text = get_clipboard_text()
                            if text:
                                active_input.print_text(text.decode(errors="ignore"))
                        else:
                            try:
                                char = chr(key).lower()
                            except ValueError:
                                pass
                            else:
                                if char.lower() in "qwertyuiopasdfghjklzxcvbnm1234567890._-":
                                    active_input.print_char(char)

            seconds = clock.tick(fps) / 1000
            pong_now = max(0, pong_now - seconds)
            self.sprites_buttons.update(seconds)
            self.sprites_inputs.update(seconds)
            main_screen.blit(self.main_image, (0, 0))
            self.sprites_buttons.draw(main_screen)
            self.sprites_inputs.draw(main_screen)
            for i, (player_id_now, nickname) in enumerate(self.players.items()):
                is_other = player_id_now != player_id
                image = self.other_box.copy() if is_other else self.your_box.copy()
                text = self.font.render(nickname, True, self.font_color)
                text_w = text.get_width()
                text_h = text.get_height()
                text_x = image.get_width() // 2 - text_w // 2
                text_y = image.get_height() // 2 - text_h // 2
                image.blit(text, (text_x, text_y))
                main_screen.blit(image, (180 - (0 if is_other else 6),
                                         375 + 60 * i - (0 if is_other else 6)))
            pygame.display.flip()
            if n:
                if pong_now == 0:
                    n.send_pickle({
                        'key': ServerKeys.NEW_INFORMATION_LOBBY,
                        'player_id': player_id,
                        'data': {
                            'nickname': self.inputs[1].get_text()
                        }
                    })
                    pong_now = pong
                data = n.get_last_data()
                if data:
                    key = data['key']
                    if key == ServerKeys.NEW_INFORMATION_LOBBY:
                        self.players = data['data']
                    elif key == ServerKeys.START_GAME:
                        global data_players, generate_seed
                        data_players = data['data']['players']
                        generate_seed = data['data']['seed']
                        self.menu_running = False
                        break


menu = Menu()
menu.start()
# print("generate_seed", generate_seed)
# walls, wall_length, lab_size = generate(width, height, generate_seed)
#
# margin_x = (width - (lab_size[0]) * wall_length) // 2
# margin_y = (height - lab_size[1] * wall_length) // 2
# for wall in walls:
#     Wall((wall[0] + margin_x, wall[1] + margin_y), bool(wall[2]))


def get_player_pos(margin_x, margin_y, wall_length):
    global data_players
    i = list(data_players.keys()).index(player_id)
    wlh = wall_length // 2  # wall length half
    tank_width, tank_height = 40, 51
    twh, thh = tank_width // 2, tank_height // 2 # tank width half, tank height half
    if i == 0:
        return margin_x + wlh - twh, margin_y + wlh - thh
    elif i == 1:
        return margin_x + wlh - twh, height - margin_y - wlh - thh
    elif i == 2:
        return width - margin_x - wlh - twh, margin_y + wlh - thh
    else:  # elif i == 3
        return width - margin_x - wlh - twh, height - margin_y - wlh - thh


def create_bullet(bullet: Bullet):
    return
    info = bullet.get_info()
    n.send_pickle({
        'key': ServerKeys.MAKE_BULLET,
        'player_id': player_id,
        'data': info
    })
    # info = n.get_info_pickle()


def load_data(data):
    for player in other_players:
        player.turret.kill()
        player.kill()
    [bullet.kill() for bullet in other_bullets]
    other_players.clear()
    other_bullets.clear()
    players = data['players']
    bullets = data['bullets']
    for player in players:
        if player is None:
            continue
        other_players.append(Tank(player['pos'],
                                  player['rotation'],
                                  player['rotation_turret'],
                                  type="other",
                                  turret_type=player['turret_type']))
        other_players[-1].motion = player['motion']
    for bullet in bullets:
        if bullet['type'] == ServerKeys.BULLET_CLASSIC:
            bullet_class = BulletClassic
        elif bullet['type'] == ServerKeys.BULLET_SHOTGUN:
            bullet_class = BulletShotgun
        elif bullet['type'] == ServerKeys.BULLET_MINIGUN:
            bullet_class = BulletMinigun
        else:
            bullet_class = BulletClassic
        other_bullets.append(bullet_class((0, 0), (0, 0), 0, False))
        other_bullets[-1].load_info(bullet)


main_screen.fill(background)
pygame.display.flip()
clock.tick()
pong = 0.04


def start_draw(general=False):
    main_screen.fill(background)
    if not player.destroyed:
        main_screen.blit(player.image, player.rect)
    sprites_bullets.draw(main_screen)
    sprites_walls.draw(main_screen)
    sprites_turrets.draw(main_screen)
    sprites_other_players.draw(main_screen)
    black_image = pygame.Surface((width, height))
    black_image.fill(pygame.Color('#491714'))
    black_image.set_alpha(60)
    main_screen.blit(black_image, (0, 0))
    if general:
        pygame.display.flip()


def count_for_start():
    global walls, wall_length, lab_size, margin_x, margin_y, player, other_players, other_bullets
    walls, wall_length, lab_size = generate(width, height, generate_seed)

    [sprite.kill() for sprite in sprites_all.sprites()]
    margin_x = (width - (lab_size[0]) * wall_length) // 2
    margin_y = (height - lab_size[1] * wall_length) // 2
    for wall in walls:
        Wall((wall[0] + margin_x, wall[1] + margin_y), bool(wall[2]))

    player = Tank(get_player_pos(margin_x, margin_y, wall_length), type='main',
                  turret_type=ServerKeys.TURRET_MINIGUN)
    other_players = []
    other_bullets = []
    n.send_pickle({
        'key': ServerKeys.CREATE_PLAYER,
        'player_id': player_id,
        'data': player.get_info()
    })
    timer1 = load_image('Timer1.png')
    timer2 = load_image('Timer2.png')
    timer3 = load_image('Timer3.png')
    timer4 = load_image('Timer4.png')
    running = True
    counter = 0
    counter_time = 0.7
    clock.tick(fps)
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                terminate()

        seconds = clock.tick(fps) / 1000
        counter += seconds
        start_draw()
        k = counter // counter_time
        if k == 0:
            image = timer1
        elif k == 1:
            image = timer2
        elif k == 2:
            image = timer3
        elif k == 3:
            image = timer4
        else:
            running = False
            break
        rect = image.get_rect()
        rect.center = main_screen.get_rect().center
        main_screen.blit(image, rect)
        pygame.display.flip()


def main_running():
    global pong, generate_seed

    pong_now = pong
    need_shot = False
    running = True
    x_vector, y_vector = 0, 0
    keys = [False] * 4
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                terminate()
            elif event.type == pygame.KEYDOWN:
                if event.key == up:
                    y_vector = -1
                    keys[0] = True
                elif event.key == left:
                    x_vector = -1
                    keys[1] = True
                elif event.key == down:
                    y_vector = 1
                    keys[2] = True
                elif event.key == right:
                    x_vector = 1
                    keys[3] = True
                elif event.key == pygame.K_ESCAPE:
                    terminate()
            elif event.type == pygame.KEYUP:
                if event.key == up:
                    y_vector = -1
                    keys[0] = False
                    y_vector = 1 if keys[2] else 0
                elif event.key == left:
                    x_vector = -1
                    keys[1] = False
                    x_vector = 1 if keys[3] else 0
                elif event.key == down:
                    y_vector = 1
                    keys[2] = False
                    y_vector = -1 if keys[0] else 0
                elif event.key == right:
                    x_vector = 1
                    keys[3] = False
                    x_vector = -1 if keys[1] else 0
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == pygame.BUTTON_LEFT:
                    need_shot = True
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == pygame.BUTTON_LEFT:
                    need_shot = False

        seconds = clock.tick(fps) / 1000
        pong_now = max(0, pong_now - seconds)
        for turret in sprites_turrets:
            turret.reload(seconds, need_shot)
        if need_shot:
            player.turret.make_shot()
        main_screen.fill(background)
        player.update(seconds, x_vector, y_vector)
        player.turret.update(seconds, pygame.mouse.get_pos())
        sprites_bullets.update(seconds)
        sprites_other_players.draw(main_screen)
        if not player.destroyed:
            main_screen.blit(player.image, player.rect)
        for other_player in sprites_other_players.sprites():
            for bullet in sprites_bullets.sprites():
                if pygame.sprite.collide_mask(other_player, bullet):
                    bullet.kill()
        sprites_bullets.draw(main_screen)
        sprites_walls.draw(main_screen)
        sprites_turrets.draw(main_screen)
        pygame.display.flip()
        if pong_now == 0:
            n.send_pickle({
                'key': ServerKeys.NEW_INFORMATION,
                'player_id': player_id,
                'data': get_info()
            })
            pong_now = pong
        else:
            for other_player in other_players:
                other_player.make_last_movement(seconds)
        data = n.get_last_data()
        if data and 'key' in data:
            if data['key'] == ServerKeys.NEW_INFORMATION:
                if data['need_restart'] and is_host:
                    generate_seed = data['data']
                    n.send_pickle({
                        'key': ServerKeys.RESTART,
                        'player_id': player_id,
                        'data': random.random()
                    })
                load_data(data['data'])
            elif data['key'] == ServerKeys.RESTART:
                generate_seed = data['data']
                print("seed", generate_seed)
                running = False


while True:
    count_for_start()
    main_running()
    sleep(1)

pygame.quit()
