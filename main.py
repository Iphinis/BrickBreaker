from random import randint

from kivy import Config
from kivy.core.audio import SoundLoader
from kivy.uix.button import Button
from kivy.uix.label import Label

Config.set('graphics', 'width', '500')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'minimum_height', '300')
Config.set('graphics', 'resizable', False)

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.widget import Widget
from kivy.properties import (
    NumericProperty, ReferenceListProperty, ObjectProperty
)
from kivy.vector import Vector
from kivy.clock import Clock


# méthode qui permet de récupérer le meilleur niveau et score enregistré dans le fichier data.txt
def get_high_score():
    with open('assets/save/data.txt', 'r') as file:
        high_score = []
        for line in file.readlines():
            high_score.append(int(line.strip("\n")))
        # renvoie un tuple de 2 éléments contenant le meilleur niveau et score, tout en supprimant les sauts à la ligne
        return high_score[:2]


# méthode qui permet de définir le meilleur niveau et score enregistré dans le fichier data.txt
def set_high_score(new_level, new_score):
    # récupérer les meilleurs scores
    highlevel, highscore = get_high_score()
    # définir les scores à enregistrer
    level = new_level if new_level > highlevel else highlevel
    score = new_score if new_score > highscore else highscore
    with open('assets/save/data.txt', 'w') as file:
        file.writelines([str(level) + "\n", str(score)])
        file.close()


sounds = {'bounce': SoundLoader.load('assets/sounds/bounce.wav'), 'start': SoundLoader.load('assets/sounds/start.wav')
    , 'victory': SoundLoader.load('assets/sounds/victory.wav'),
          'game_over': SoundLoader.load('assets/sounds/game_over.wav')}


def play_sound(sound_name):
    sound = sounds[sound_name]
    sound.play()


def clamp(value, minimum, maximum):
    return max(min(value, maximum), minimum)


# classe de la brique
class Brick(Widget):
    r = NumericProperty(0)
    g = NumericProperty(0)
    b = NumericProperty(0)
    a = NumericProperty(0)

    # constructeur de la classe Brick
    def __init__(self, game, color, **kwargs):
        super(Brick, self).__init__(**kwargs)
        self.game = game
        self.health = 1
        self.alive = True

        self.c = color
        self.r = self.c[0]
        self.g = self.c[1]
        self.b = self.c[2]
        self.a = self.c[3]

    # méthode qui appelle la fonction rebondir de la balle
    # si l'objet qui fait collision est la balle
    # et supprime la brique du layout si elle n'a plus de vie
    def damage(self, ball):
        if not self.alive:
            return
        if self.collide_widget(ball):
            play_sound('bounce')
            ball.bounce(self.center_x)#Window.width / 2)
            self.health -= 1
            self.game.score += randint(1, 3)
            if self.health <= 0:
                self.destroy()

    def destroy(self):
        self.alive = False
        self.a = 0
        # mettre à jour le visuel de la brique
        self.game.layout.grid.children[self.game.layout.get_brick(self)] = self
        if self.game.layout.bricks_count() == 0:
            if self.game.level == self.game.levelToWin:
                self.game.victory()
            else:
                self.game.reset_game(False)


# classe du layout du jeu (hérite de FloatLayout)
class GameLayout(FloatLayout):
    # constructeur de la classe GameLayout
    def __init__(self, **kwargs):
        self.grid = None
        super(GameLayout, self).__init__(**kwargs)

    def get_brick(self, brick):
        return self.grid.children.index(brick)

    # méthode qui renvoie le nombre de briques restantes
    def bricks_count(self):
        count = 0
        for brick in self.grid.children:
            if brick.alive:
                count += 1
        return count


# classe de la balle
class Ball(Widget):
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    velocity = ReferenceListProperty(velocity_x, velocity_y)

    max_velocity = 4

    # méthode qui limite la vélocité de la balle
    def clamp_velocity(self):
        self.velocity_x = clamp(self.velocity_x, -self.max_velocity, self.max_velocity)
        self.velocity_y = clamp(self.velocity_y, -self.max_velocity, self.max_velocity)

    # méthode qui fait rebondir la balle
    def bounce(self, other):
        speedup = 1.1
        offset = 0.02 * Vector(self.center_x - other, 0)

        self.clamp_velocity()

        # Appliquer la vélocité à la balle
        self.velocity = speedup * (offset - self.velocity)

    # méthode qui fait bouger la balle
    def move(self):
        self.pos = Vector(*self.velocity) + self.pos


# classe de la planche qui fait office de joueur
class Paddle(Widget):
    # méthode qui appelle la fonction rebondir de la balle
    # si l'objet qui fait collision est la balle
    def bounce_ball(self, ball):
        if self.collide_widget(ball):
            ball.bounce(self.center_x)


# classe du jeu casse-briques
class BrickBreakerGame(Widget):
    # variables liées au fichier kivy
    ball = ObjectProperty(None)
    paddle = ObjectProperty(None)

    level = NumericProperty(0)
    score = NumericProperty(0)
    max_lives = 3
    lives = NumericProperty(max_lives)

    # variables liées au jeu
    layout = None
    levelToWin = 5
    isPlaying = False

    panel = None

    # méthode qui va créer un menu dynamiquement en fonction des widgets renseignés et l'afficher
    def create_panel(self, widgets):
        if widgets is None:
            return
        self.panel = GridLayout(pos=[Window.width / 2 - 50, Window.height / 2 - 75], cols=1)

        if type(widgets) != list:
            self.panel.add_widget(widgets)
        else:
            for widget in widgets:
                self.panel.add_widget(widget)

        self.add_widget(self.panel)

    def play(self, instance):
        self.remove_widget(self.panel)
        self.panel = None
        if self.level != 0:
            self.reset_game(True)
        else:
            self.reset_game(False)

    # méthode qui crée les briques
    def create_bricks(self, rows, cols=4, start_color=[0.52, 0.18, 0.11, 1]):
        self.layout.grid.clear_widgets()

        for y in range(rows):
            color = [v + (y / rows) for v in start_color]
            for x in range(cols):
                self.add_brick(color)

    # méthode qui ajoute une brique au GridLayout appelé grid
    def add_brick(self, c):
        brick = Brick(game=self, color=c)
        self.layout.grid.add_widget(brick)

    def update(self, dt):
        if not self.isPlaying:
            return
        self.ball.move()
        self.paddle.bounce_ball(self.ball)
        for brick in self.layout.grid.children:
            brick.damage(self.ball)

        if self.ball.y < 0:
            self.lose_life()

        # bounce off top
        if self.ball.top > self.height:
            self.ball.velocity_y *= -1

        # bounce off left and right
        if self.ball.x < 0 or self.ball.right > self.width:
            self.ball.velocity_x *= -1

    def serve_ball(self):
        self.paddle.pos = [Window.width / 2, self.paddle.height + 45]
        self.ball.velocity = Vector(randint(-3, 3), -1)

    def on_touch_move(self, touch):
        if not self.isPlaying:
            return
        self.paddle.center_x = touch.x

    def lose_life(self):
        self.lives -= 1
        if self.lives <= 0:
            self.game_over()
        else:
            play_sound('start')
            self.serve_ball()
            self.ball.pos = [Window.width / 2, Window.height / 2]

    def victory(self):
        self.isPlaying = False
        play_sound('victory')

        set_high_score(self.level, self.score)

        highlevel, highscore = get_high_score()

        widgets = [Label(text="You won!", font_size=30, color=[1, 0.84, 0, 1]), Button(text="Restart", font_size=20),
                   Label(text="High Level: " + str(highlevel) + "\nHigh Score: " + str(highscore), font_size=20, color=[1, 1, 1, 1])]
        widgets[1].bind(on_press=self.play)
        self.create_panel(widgets)

    def game_over(self):
        self.isPlaying = False
        play_sound('game_over')

        set_high_score(self.level, self.score)

        highlevel, highscore = get_high_score()

        widgets = [Label(text="You lost!", font_size=30, color=[1, 0.14, 0.14, 1]), Button(text="Restart", font_size=20),
                   Label(text="High Level: " + str(highlevel) + "\nHigh Score: " + str(highscore), font_size=20, color=[1, 1, 1, 1])]
        widgets[1].bind(on_press=self.play)
        self.create_panel(widgets)

    def reset_game(self, reset_values):
        # Réinitialiser les variables si le bouléen reset_values est vrai
        if reset_values:
            self.level = 1
            self.lives = 1
            self.score = 0
        else:
            self.level += 1
            play_sound('start')

        # Réinitialiser les positions des objets et servir la balle
        self.ball.pos = [Window.width / 2, Window.height / 2]
        self.serve_ball()

        # Créer les briques pour la partie d'après
        self.create_bricks(self.level * 2, self.level * 2 if self.level * 2 % 4 == 0 else 4)
        self.isPlaying = True


# classe de l'application casse-brique
class BrickBreakerApp(App):
    def build(self):
        game = BrickBreakerGame()

        btn = Button(text="Play", font_size=20, size=[100, 40])
        btn.bind(on_press=game.play)

        game.create_panel(btn)

        Clock.schedule_interval(game.update, 1.0 / 60.0)
        grid = GridLayout(cols=4, pos_hint={'top': 1}, size_hint=[1, 0.5],
                          row_default_height=30, row_force_default=True)
        layout = GameLayout()
        layout.add_widget(game)
        layout.add_widget(grid)
        layout.grid = layout.children[0]

        game.layout = layout
        return layout


if __name__ == '__main__':
    BrickBreakerApp().run()