import pygame

class Gol(pygame.sprite.Sprite):
    def __init__(self, sir, vis, imag, koj, sirina, visina, platforma_visina, koji):
        super(Gol, self).__init__()
        self.image=imag.convert_alpha()
        self.sirina=sir
        self.visina=vis
        self.koji=koji
        self.precka=0
        if(koj==1):self.rect=self.image.get_rect(center=(self.sirina/2, visina-platforma_visina-self.visina/2))
        else: self.rect=self.image.get_rect(center=(sirina-self.sirina/2, visina-platforma_visina-self.visina/2))
        self.surface=pygame.Surface((self.sirina, self.visina))
        self.surface.blit(self.image, self.rect)
