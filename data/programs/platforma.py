import pygame
import re

class Platforma(pygame.sprite.Sprite):
    def __init__(self, sir, vis, sirc, visc):
        super(Platforma, self).__init__()
        self.image=pygame.transform.smoothscale(pygame.image.load("data/images/dio_poda1.PNG"), (sir, vis)).convert()
        self.rect=self.image.get_rect(center = (sirc, visc))
        self.surface=pygame.Surface((sir, vis))
        self.surface.blit(self.image, self.rect)
