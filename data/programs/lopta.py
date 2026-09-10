import pygame
import random
import math
import copy
import time
from time import sleep
from data.programs.PokretniTeren import PokretniTeren
from data.programs.Teren import Teren
from pygame.locals import *
vec=pygame.math.Vector2
kolko=0

image_lopti={}
image_lopti["data/images/lopta_bomba.png"]=pygame.image.load("data/images/lopta_bomba.png")
image_lopti["data/images/lopta.png"]=pygame.image.load("data/images/lopta.png")
image_lopti["data/images/bouncy_lopta.png"]=pygame.image.load("data/images/bouncy_lopta.png")
image_lopti["data/images/dead_lopta.png"]=pygame.image.load("data/images/dead_lopta.png")

class Lopta(pygame.sprite.Sprite):
    def __init__(self, pos, vel, acc, radius, ime_lopte, koja_sam, lopta_radius_mid, lopta_bomba_dod_visina, iz_topa_sam, elasticnost, dodatno):
        super(Lopta, self).__init__()
        self.pos=vec(pos)
        self.vel=vec(vel)
        self.acc=vec(acc)
        self.radius=radius
        self.vani=0
        self.koja_sam=koja_sam
        self.masa=5
        self.izlazim=0
        self.bomba_sam=[0,0]
        self.iz_topa_sam=iz_topa_sam
        self.za_fade=255
        self.dirala_nes=False
        self.dupla_sam=-1
        self.elasticnost=elasticnost
        self.ime=ime_lopte
        self.zadnji_diro=-1
        self.previous_frame_collision_group=-1

        if(iz_topa_sam==-5):
            self.iz_topa_sam=0
            self.dupla_sam=600

        self.image=pygame.transform.smoothscale(image_lopti[ime_lopte], (self.radius*2, self.radius*2))
        self.rect=self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        self.surface=pygame.Surface((self.radius*2, self.radius*2))
        self.surface.blit(self.image, self.rect)

        self.image_lopta_bomba=pygame.transform.smoothscale(image_lopti["data/images/lopta_bomba.png"], (self.radius*2, self.radius*2+lopta_bomba_dod_visina*(self.radius/lopta_radius_mid)))
        self.rect_lopta_bomba=self.image_lopta_bomba.get_rect(midbottom=self.rect.midbottom)

        if(len(dodatno)>0):
            self.vani=dodatno[0]
            self.masa=dodatno[1]
            self.izlazim=dodatno[2]
            self.bomba_sam[0]=dodatno[3]
            self.bomba_sam[1]=dodatno[4]
            self.za_fade=dodatno[5]
            self.dirala_nes=dodatno[6]
            self.dupla_sam=dodatno[7]
            self.zadnji_diro=dodatno[8]
        
    def update_move(self, stipke, gravitacija, OTPOR_ZRAKA, FRIC, platforma, sirina, llopta11, dodir_zvuk, za_editor):
        self.acc=vec(0,gravitacija)
        prov=False
        jel_dodir_zvuk=0

        if(self.rect.bottom+1<platforma.rect.midtop[1]):
            self.acc.x+=self.vel.x*OTPOR_ZRAKA
        else:
            self.acc.x+=self.vel.x*FRIC

        pos1=copy.deepcopy(self.pos)
        self.vel+=self.acc
        self.pos+=self.vel+0.5*self.acc

        if(za_editor):
            if stipke[K_RIGHT]:
                self.vel.x+=1
            if stipke[K_LEFT]:
                self.vel.x-=1
            if stipke[K_UP]:
                self.vel.y-=0.5

        
        if self.pos.x+self.radius>=sirina:
            self.acc.x*=-self.elasticnost
            self.vel.x*=-self.elasticnost
            pomx, pomy = self.pos.x-pos1.x, self.pos.y-pos1.y
            if(not pomx==0):pomy*=(sirina-self.radius-pos1.x)/pomx
            self.pos.x=sirina-self.radius-1
            self.pos.y=pos1.y+pomy
            prov=True
            jel_dodir_zvuk=1
        if self.pos.x-self.radius<0:
            self.acc.x*=-self.elasticnost
            self.vel.x*=-self.elasticnost
            pomx, pomy = self.pos.x-pos1.x, self.pos.y-pos1.y
            if(not pomx==0):pomy*=(self.radius-pos1.x)/pomx
            self.pos.y=pos1.y+pomy
            self.pos.x=self.radius+1
            prov=True
            jel_dodir_zvuk=1
        if self.rect.top<0:
            self.vel.y*=-self.elasticnost
            self.acc.y*=-self.elasticnost
            self.pos.y=self.radius*2+1
            jel_dodir_zvuk=1

        
        self.rect.center = self.pos
        self.rect_lopta_bomba.midbottom = self.rect.midbottom

        self.vel.x=min(self.vel.x, 75)
        self.vel.y=min(self.vel.y, 75)
        self.vel.x=max(self.vel.x, -75)
        self.vel.y=max(self.vel.y, -75)
        return (prov, jel_dodir_zvuk)

    def update_col(self, platforme):
        hits=pygame.sprite.spritecollide(self, platforme, False)
        prov=False
        jel_dodir_zvuk=0
        if self.vel.y > 0:
            if hits:
                if(abs(self.vel.y)>0.5 and self.vel.x!=0):
                    jel_dodir_zvuk=1
                self.pos.y=hits[0].rect.top -self.radius+1
                self.vel.y*=-self.elasticnost*0.8
                prov=True
                self.dirala_nes=True
                
        self.rect.center = self.pos
        self.rect_lopta_bomba.midbottom = self.rect.midbottom
        self.vel.x=min(self.vel.x, 75)
        self.vel.y=min(self.vel.y, 75)
        self.vel.x=max(self.vel.x, -75)
        self.vel.y=max(self.vel.y, -75)
        return (prov, jel_dodir_zvuk)

    def reflect(self, igr, platforma, lista_igraca, koji_su, lista_dropova, lista_abilitija):
        global kolko
        jel_dodir_zvuk=0

        for i in range(len(lista_igraca)):
            igr1=lista_igraca[i]
            for j in range(i+1, len(lista_igraca)):
                igr2=lista_igraca[j]
                #if(self.rect.bottom>max(igr1.pos.y, igr2.pos.y) and ((self.pos.x>=igr1.pos.x and self.pos.x<=igr2.pos.x and igr2.rect.left-igr1.rect.right<=self.radius) or (self.pos.x>=igr2.pos.x and self.pos.x<=igr1.pos.x and igr1.rect.left-igr2.rect.right<=self.radius))):
                if(self.rect.bottom>max(igr1.pos.y, igr2.pos.y) and self.pos.distance_to(igr1.pos)<=self.radius+igr1.radius+1 and self.pos.distance_to(igr2.pos)<=self.radius+igr2.radius+1):
                    self.izlazim=1
                    self.vel.y=random.randint(-17,-10)
                    self.pos.y-=50
                    self.vel.x=random.randint(-6,6)
                    self.acc.x=0
                    if(igr1.pos.x<igr2.pos.x):
                        igr1.vel.x=-7
                        igr2.vel.x=7
                        igr1.pos.x-=5
                        igr2.pos.x+=5
                    else:
                        igr1.vel.x=7
                        igr2.vel.x=-7
                        igr1.pos.x+=5
                        igr2.pos.x-=5

                    return

                    

        for drop in lista_dropova:
            if(self.pos.y>igr.pos.y and (abs(drop.rect.left-self.rect.right)<=3 or abs(self.rect.left-drop.rect.right)<=3) and (drop.stanje==28 or drop.stanje==29)):
                self.vel.y=-20
                self.pos.y-=50
                self.vel.x=random.randint(-10,10)
                self.acc.x=0

        for stup in lista_abilitija:
            if(not stup.vrsta==1):continue
            if(self.pos.y>igr.pos.y and (abs(stup.rect.left-self.rect.right)<=3 or abs(self.rect.left-stup.rect.right)<=3)):
                self.vel.y=-20
                self.pos.y-=50
                self.acc.x=0
                if(self.pos.x>stup.pos.x):self.vel.x=random.randint(0,10)
                else:self.vel.x=random.randint(-10,0)
        
        if platforma.rect.top-self.rect.center[1]<=self.radius+1:
            
            if platforma.rect.top-igr.rect.center[1]>igr.radius:
                if self.pos.x>=igr.pos.x:
                    self.pos.x+=10
                    self.vel.x+=10*igr.masa/100
                else:
                    self.pos.x-=10
                    self.vel.x-=10*igr.masa/100
            else:
                self.vel.x=igr.vel.x*2
                if self.pos.x>=igr.pos.x:
                    self.pos.x+=3
                    if(self.vel.y>0):self.vel.y=0
                else:
                    self.pos.x-=3
                    if(self.vel.y>0):self.vel.y=0
        else:
            if(self.pos.x<=igr.pos.x):
                self.pos.x-=1
            else:
                self.pos.x+=1

            if(self.pos.y<=igr.pos.y):
                self.pos.y-=1
            else:
                self.pos.y+=1
            jel_dodir_zvuk=1

        self.rect.center=self.pos
        self.rect_lopta_bomba.midbottom = self.rect.midbottom
        
        self.vel.x=min(self.vel.x, 75)
        self.vel.y=min(self.vel.y, 75)
        self.vel.x=max(self.vel.x, -75)
        self.vel.y=max(self.vel.y, -75)
        return jel_dodir_zvuk

    def provjera_lopta_ability_bomba(self, igrac, lista_igraca, eksplozija_sirina, jel_prom):
        if(self.bomba_sam[0]==0):return []
        if(igrac==self.bomba_sam[1] and self.bomba_sam[0]<=5 and not jel_prom):return []
        
        lista_ig=[]
        if(not igrac==-1):lista_ig.append(igrac)
        for i in range(len(lista_igraca)):
            igr=lista_igraca[i]
            if(igr==igrac):continue
            v1=vec(igr.pos)
            v2=vec(self.pos)
            dist=v1.distance_to(v2)
            if dist<=igr.radius+eksplozija_sirina/2:              
                lista_ig.append(igr)

        if(not jel_prom):self.bomba_sam=[0,0]
        return lista_ig

    def provjera_za_duplu(self, lista_igraca, lista_lopti, teren, lista_dropova):
        jel_diram=False
        for igrac in lista_igraca:
            if(self.pos.distance_to(igrac.pos)<=self.radius+igrac.radius+1):jel_diram=True

        for lopta in lista_lopti:
            if(self==lopta):continue
            if(self.pos.distance_to(lopta.pos)<=self.radius+lopta.radius+1):jel_diram=True

        lopta_mask=pygame.mask.from_surface(self.image)
        for tr in teren:
            if(not isinstance(tr, Teren) and not isinstance(tr, PokretniTeren)):continue
            if(tr.koji==7):
                if(self.pos.distance_to(tr.pos)<=self.radius+tr.radius+1):jel_diram=True
            elif(tr.koji==1):
                tr_mask=pygame.mask.from_surface(tr.surf)
                offset=(self.rect[0]-tr.rect[0]-1, self.rect[1]-tr.rect[1]-1)
                overlap=tr_mask.overlap(lopta_mask, offset)
                if(not overlap==None):jel_diram=True
            elif(tr.koji==5 or tr.koji==6):
                tr_mask=pygame.mask.from_surface(tr.image)
                offset=(self.rect[0]-tr.rect[0], self.rect[1]-tr.rect[1])
                overlap=tr_mask.overlap(lopta_mask, offset)
                if(not overlap==None):jel_diram=True

        for drop in lista_dropova:
            offset=(self.rect[0]-drop.rect1[0], self.rect[1]-drop.rect1[1])
            overlap=drop.mask.overlap(lopta_mask, offset)
            if(not overlap==None):jel_diram=True

        if(not jel_diram):self.dirala_nes=True
