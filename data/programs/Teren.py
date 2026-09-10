import pygame
import math
import copy
import time
from data.programs.Edge import Edge
from data.programs.Cvor import Cvor
vec=pygame.math.Vector2

class Teren(pygame.sprite.Sprite):
    def __init__(self, cvorovi, veze, sirina, visina):
        super(Teren, self).__init__()
        self.cvorovi=cvorovi
        self.veze=veze
        self.edgevi=[]
        self.koji=1
        self.sirina_ekrana=sirina
        self.visina_ekrana=visina
        self.surf=pygame.Surface((sirina, visina), pygame.SRCALPHA)
        self.rect=self.surf.get_rect(topleft=(0,0))
        self.mask=-1

    def stvori_edgeve(self):
        sredio=[]
        for i in range(len(self.cvorovi)):
            sredio.append([])
            for j in range(len(self.cvorovi)):
                sredio[i].append(0)

        for i in range(len(self.veze)):
            if(sredio[self.veze[i][0]][self.veze[i][1]]==1):continue
            sredio[self.veze[i][0]][self.veze[i][1]]=1
            sredio[self.veze[i][1]][self.veze[i][0]]=1
            cvor1=self.cvorovi[self.veze[i][0]]
            cvor2=self.cvorovi[self.veze[i][1]]
            edge=Edge(cvor1, cvor2, self.veze[i][2], self.veze[i][3], self.veze[i][4])
            self.edgevi.append(edge)

    def render(self):
        self.surf=pygame.Surface((self.sirina_ekrana, self.visina_ekrana), pygame.SRCALPHA)
        for edge in self.edgevi:edge.render(self.surf)
        for cvor in self.cvorovi:cvor.render(self.surf)
        self.mask=pygame.mask.from_surface(self.surf)

    def update_rotation(self, factor1, factor2):
        ima=False
        for cvor in self.cvorovi:
            if(not cvor.has_rotation_point):continue
            ima=True
            cvor.update_rotation(factor1, factor2)
        
        if(ima):self.render()

    def postavi(self):
        for cvor in self.cvorovi:
            cvor.pos=copy.deepcopy(cvor.org_pos)
        self.render()

    def nadi_sudar(self, lopta, llopta11):
        tr=None
        kol=0

        for edge in self.edgevi:
            pos1=edge.cvor1.pos
            pos2=edge.cvor2.pos
            dis=abs((pos2.x-pos1.x)*(lopta.pos.y-pos1.y)-(lopta.pos.x-pos1.x)*(pos2.y-pos1.y))/math.sqrt(math.pow(pos2.x-pos1.x,2)+math.pow(pos2.y-pos1.y,2))
            
            if(dis<=edge.radius+lopta.radius):
                
                smjer=(edge.cvor1.pos-edge.cvor2.pos).normalize()
                smjer1=smjer.rotate(90)
                smjer2=smjer.rotate(-90)
                pos_t1=llopta11[lopta.koja_sam][0]+smjer1*dis
                pos_t2=llopta11[lopta.koja_sam][0]+smjer2*dis
                dis1=abs((pos2.x-pos1.x)*(pos_t1.y-pos1.y)-(pos_t1.x-pos1.x)*(pos2.y-pos1.y))/math.sqrt(math.pow(pos2.x-pos1.x,2)+math.pow(pos2.y-pos1.y,2))
                dis2=abs((pos2.x-pos1.x)*(pos_t2.y-pos1.y)-(pos_t2.x-pos1.x)*(pos2.y-pos1.y))/math.sqrt(math.pow(pos2.x-pos1.x,2)+math.pow(pos2.y-pos1.y,2))
                
                if(dis1<dis2):pos_t=pos_t1
                else:pos_t=pos_t2

                uk_dis=edge.cvor1.pos.distance_to(edge.cvor2.pos)
                uvj1=pos_t.distance_to(edge.cvor1.pos)>uk_dis or pos_t.distance_to(edge.cvor2.pos)>uk_dis

                smjer=(edge.cvor1.pos-edge.cvor2.pos).normalize()
                smjer1=smjer.rotate(90)
                smjer2=smjer.rotate(-90)
                pos_t1=llopta11[lopta.koja_sam][0]+llopta11[lopta.koja_sam][1]+smjer1*dis
                pos_t2=llopta11[lopta.koja_sam][0]+llopta11[lopta.koja_sam][1]+smjer2*dis
                dis1=abs((pos2.x-pos1.x)*(pos_t1.y-pos1.y)-(pos_t1.x-pos1.x)*(pos2.y-pos1.y))/math.sqrt(math.pow(pos2.x-pos1.x,2)+math.pow(pos2.y-pos1.y,2))
                dis2=abs((pos2.x-pos1.x)*(pos_t2.y-pos1.y)-(pos_t2.x-pos1.x)*(pos2.y-pos1.y))/math.sqrt(math.pow(pos2.x-pos1.x,2)+math.pow(pos2.y-pos1.y,2))
                
                if(dis1<dis2):pos_t=pos_t1
                else:pos_t=pos_t2

                uvj2=pos_t.distance_to(edge.cvor1.pos)>uk_dis or pos_t.distance_to(edge.cvor2.pos)>uk_dis

                if(uvj1 and uvj2):continue

                smjer=(edge.cvor1.pos-edge.cvor2.pos).normalize()
                smjer1=smjer.rotate(90)
                smjer2=smjer.rotate(-90)
                pos_t1=lopta.pos+smjer1*dis
                pos_t2=lopta.pos+smjer2*dis
                dis1=abs((pos2.x-pos1.x)*(pos_t1.y-pos1.y)-(pos_t1.x-pos1.x)*(pos2.y-pos1.y))/math.sqrt(math.pow(pos2.x-pos1.x,2)+math.pow(pos2.y-pos1.y,2))
                dis2=abs((pos2.x-pos1.x)*(pos_t2.y-pos1.y)-(pos_t2.x-pos1.x)*(pos2.y-pos1.y))/math.sqrt(math.pow(pos2.x-pos1.x,2)+math.pow(pos2.y-pos1.y,2))
                
                if(dis1<dis2):pos_t=pos_t1
                else:pos_t=pos_t2

                tr1=Cvor(pos_t, edge.radius, edge.masa, edge.boja, [edge.has_rotation_point, edge.rotation_point_pos, edge.rotation_speed], edge.cvor1.grupa)

                lopta_pos_copy=copy.deepcopy(lopta.pos)

                pom=llopta11[lopta.koja_sam][0]-lopta.pos
                for i in range(100):
                    lopta.pos+=pom/100
                    lopta.rect.center=lopta.pos

                    if(edge.has_rotation_point):
                        edge.cvor1.rotate_back_for_collision(-1, 100)
                    
                    pos1=edge.cvor1.pos
                    pos2=edge.cvor2.pos
                    dis=abs((pos2.x-pos1.x)*(lopta.pos.y-pos1.y)-(lopta.pos.x-pos1.x)*(pos2.y-pos1.y))/math.sqrt(math.pow(pos2.x-pos1.x,2)+math.pow(pos2.y-pos1.y,2))

                    smjer=(edge.cvor1.pos-edge.cvor2.pos).normalize()
                    smjer1=smjer.rotate(90)
                    smjer2=smjer.rotate(-90)
                    pos_t1=lopta.pos+smjer1*dis
                    pos_t2=lopta.pos+smjer2*dis
                    dis1=abs((pos2.x-pos1.x)*(pos_t1.y-pos1.y)-(pos_t1.x-pos1.x)*(pos2.y-pos1.y))/math.sqrt(math.pow(pos2.x-pos1.x,2)+math.pow(pos2.y-pos1.y,2))
                    dis2=abs((pos2.x-pos1.x)*(pos_t2.y-pos1.y)-(pos_t2.x-pos1.x)*(pos2.y-pos1.y))/math.sqrt(math.pow(pos2.x-pos1.x,2)+math.pow(pos2.y-pos1.y,2))
                    
                    if(dis1<dis2):pos_t=pos_t1
                    else:pos_t=pos_t2

                    tr1=Cvor(pos_t, edge.radius, edge.masa, edge.boja, [edge.has_rotation_point, edge.rotation_point_pos, edge.rotation_speed], edge.cvor1.grupa)
                    
                    if(lopta.pos.distance_to(tr1.pos)>lopta.radius+tr1.radius):
                        break

                kol=i+1

                uk_dis=edge.cvor1.pos.distance_to(edge.cvor2.pos)
                if(pos_t.distance_to(edge.cvor1.pos)>uk_dis or pos_t.distance_to(edge.cvor2.pos)>uk_dis):
                    lopta.pos=lopta_pos_copy
                else:
                    tr=tr1
                lopta.rect.center=lopta.pos
        
        for cvor in self.cvorovi:
            if(lopta.pos.distance_to(cvor.pos)<=cvor.radius+lopta.radius):
                
                pom=llopta11[lopta.koja_sam][0]-lopta.pos
                for i in range(100):
                    lopta.pos+=pom/100
                    lopta.rect.center=lopta.pos

                    if(cvor.has_rotation_point):
                        cvor.rotate_back_for_collision(-1, 100)

                    if(lopta.pos.distance_to(cvor.pos)>lopta.radius+cvor.radius):
                        break

                kol=i+1
                tr=cvor

        if(not tr==None and tr.has_rotation_point):
            tr.calculate_velocity()

        """if(not tr==None and lopta.previous_frame_collision_group==tr.grupa):
            tr.rotate_back_for_collision(1, kol/100)
            pom=lopta.pos-tr.rotation_point_pos
            pom=pom.rotate(tr.rotation_speed/(kol/100))
            lopta.pos=tr.rotation_point_pos+pom
            print(kol)"""

        if(not tr==None):lopta.previous_frame_collision_group=tr.grupa
                
        return tr
        
