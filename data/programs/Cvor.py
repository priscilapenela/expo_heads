import pygame
import math
import copy
vec=pygame.math.Vector2

omjer=1

class Cvor(pygame.sprite.Sprite):
    def __init__(self, pos, radius, masa, boja, rotation, grupa):
        super(Cvor, self).__init__()
        self.pos=vec(pos)
        self.radius=radius
        self.masa=masa
        self.boja=boja
        self.vel=vec(0,0)
        self.koji=1
        self.has_rotation_point=rotation[0]
        self.rotation_point_pos=rotation[1]
        self.rotation_speed=rotation[2]
        self.grupa=grupa
        self.clanovi_grupe=[]
        self.org_pos=copy.deepcopy(self.pos)

        dist=self.rotation_point_pos.distance_to(self.pos)
        self.speed=2*dist*math.pi*abs(self.rotation_speed)/6/60

    def calculate_group(self, nodes):
        for node in nodes:
            if(not node==self and node.grupa==self.grupa):
                self.clanovi_grupe.append(node)

    def calculate_velocity(self):
        r=self.pos-self.rotation_point_pos
        r=r.normalize()
        if(self.rotation_speed>0):r=r.rotate(90)
        else:r=r.rotate(-90)
        self.vel=self.speed*r

    def update_rotation(self, factor1, factor2):
        #factor1 --> -1 kad trebamo vracat za collision, 1 za normalni rad
        #factor2 --> kolko je umanjen korak vracanja za collision

        pom=self.pos-self.rotation_point_pos
        pom=pom.rotate(factor1*self.rotation_speed/factor2)
        self.pos=self.rotation_point_pos+pom

    def rotate_back_for_collision(self, factor1, factor2):
        self.update_rotation(factor1, factor2)

        for node in self.clanovi_grupe:
            node.update_rotation(factor1, factor2)

    def render(self, surface):
        pygame.draw.circle(surface, self.boja, (round(self.pos.x), round(self.pos.y)), self.radius)
        
