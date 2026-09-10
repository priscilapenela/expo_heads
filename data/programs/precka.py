import pygame
import math

vec=pygame.math.Vector2

class Precka(pygame.sprite.Sprite):
    def __init__(self, pozicijax, pozicijay, golsirina1, sirina, gol):
        super(Precka, self).__init__()
        self.surf=pygame.Surface((golsirina1, 6))
        self.surf.fill((0,0,0))
        self.rect=self.surf.get_rect(center=(pozicijax, pozicijay))
        self.masa=100
        self.radius=3
        self.pos=vec(pozicijax, pozicijay)
        self.vel=vec(0,0)
        self.mask=pygame.mask.from_surface(self.surf)
        self.gol=gol
        if(pozicijax<sirina/2):self.pos.x=self.rect.right-3
        else:self.pos.x=self.rect.left+3
        self.pos1=vec(pozicijax, pozicijay)

    def update(self, visina, platforma_visina):
        self.pos1.y=visina-platforma_visina-self.gol.visina+5
        self.rect=self.surf.get_rect(center=(round(self.pos1.x), round(self.pos1.y)))
        self.pos.y=self.rect.center[1]
