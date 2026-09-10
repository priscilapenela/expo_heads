import pygame
import os
import time
import copy
import math
vec=pygame.math.Vector2

class RotatableImage():
    def __init__(self, pos, width, height, image):
        super(RotatableImage, self).__init__()
        self.pos=vec(pos)
        self.width=width
        self.height=height
        self.radius=self.width/2
        self.angle=0
        self.org_image=pygame.transform.smoothscale(image, (width, height)).convert_alpha()
        self.image=self.org_image
        self.rect=self.image.get_rect(center=self.pos)

    def update(self):
        self.rect=self.image.get_rect(center=self.pos)

    def rotate(self, angle):
        self.angle+=angle
        if(self.angle>=360):self.angle%=360
        self.image=pygame.transform.rotate(self.org_image, -self.angle)
        self.rect=self.image.get_rect(center=self.pos)

    def render(self, surf, offset):
        rect=rect=self.image.get_rect(center=self.pos+offset)
        surf.blit(self.image, rect)
        #pygame.draw.rect(surf, (235, 225, 52), self.rect, 2)
