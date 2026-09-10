import pygame
import math
import copy
from data.programs.Cvor import Cvor
vec=pygame.math.Vector2

class Edge(pygame.sprite.Sprite):
    def __init__(self, cvor1, cvor2, radius, masa, boja):
        super(Edge, self).__init__()
        self.cvor1=cvor1
        self.cvor2=cvor2
        self.radius=radius
        self.masa=masa
        self.boja=boja
        self.has_rotation_point=self.cvor1.has_rotation_point
        self.rotation_point_pos=self.cvor1.rotation_point_pos
        self.rotation_speed=self.cvor1.rotation_speed

    def render(self, surface):
        smjer=(self.cvor1.pos-self.cvor2.pos).normalize()
        smjer1=smjer.rotate(90)
        smjer2=smjer.rotate(-90)
        pos1=vec(round(self.cvor1.pos.x), round(self.cvor1.pos.y))+smjer1*self.radius
        pos2=vec(round(self.cvor2.pos.x), round(self.cvor2.pos.y))+smjer1*self.radius
        pos3=vec(round(self.cvor2.pos.x), round(self.cvor2.pos.y))+smjer2*self.radius
        pos4=vec(round(self.cvor1.pos.x), round(self.cvor1.pos.y))+smjer2*self.radius
        pygame.draw.polygon(surface, self.boja, [pos1, pos2, pos3, pos4])
        """print(pos1)
        print(pos2)
        print(pos3)
        print(pos4)
        print()"""
        

