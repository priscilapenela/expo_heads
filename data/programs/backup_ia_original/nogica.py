import pygame
import random
from pygame.locals import *
vec=pygame.math.Vector2

image_nogica={}
image_nogica["data/images/nogica1.png"]=pygame.image.load("data/images/nogica1.png")
image_nogica["data/images/nogica2.png"]=pygame.image.load("data/images/nogica2.png")

# ─── Expo Heads: dificultad IA TOP #1 ────────────────────────────
# Mejora la reacción de patada de los jugadores bot.
EXPO_TOP1_HARD_AI = True


class Nogica(pygame.sprite.Sprite):
    def __init__(self, sir, vis, koj, igr, delay, nogica_image1):
        super(Nogica, self).__init__()
        self.igr=igr
        self.pos=vec(self.igr.rect.midbottom)
        self.sir=sir
        self.vis=vis
        self.koji=koj
        self.delay=delay
        self.pos.y+=self.vis/7
        self.img=image_nogica[nogica_image1]
        self.img1=nogica_image1
        
        if(self.igr.za_koga==1):self.img=pygame.transform.flip(self.img, True, False)

        self.image=pygame.transform.smoothscale(self.img, (self.sir, self.vis))
        self.rect=self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        self.surface=pygame.Surface((self.sir, self.vis))
        self.surface.blit(self.image, self.rect)

        if(self.delay>0):
            if(self.igr.za_koga==1):self.image=pygame.transform.rotate(self.image,90)
            elif(self.igr.za_koga==2):self.image=pygame.transform.rotate(self.image,-90)
            if(self.igr.za_koga==1):self.pos.x=self.igr.rect.right+7
            else:self.pos.x=self.igr.rect.left-7
            self.pos.y=self.igr.pos.y+self.igr.radius/7
        
            self.rect=self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
            self.rect.center=self.pos

    def postavi(self):
        self.image=pygame.transform.smoothscale(self.img, (self.sir, self.vis))
        if(self.delay>0):
            if(self.igr.za_koga==1):
                self.image=pygame.transform.rotate(self.image,90)
                self.pos.x=self.igr.rect.right+7
            else:
                self.image=pygame.transform.rotate(self.image,-90)
                self.pos.x=self.igr.rect.left-7
            self.pos.y=self.igr.pos.y+self.igr.radius/7
        else:
            self.pos=vec(self.igr.rect.midbottom)
            self.pos.y+=self.vis/7

        self.rect.center=self.pos
        
    def update(self, ev, prvi, igrac_radius_mid, igrac_radius_max, loptaa, kontrole, nogica_image1, nogica_image2, poss, broj_lopti):
        if(prvi):return
        
        for event in ev:
            if event.type==KEYDOWN:
                if event.key==kontrole[0][3] and self.igr.za_koga==1 and self.delay==0 and self.img1=="data/images/nogica1.png" and not self.igr.bot and not self.igr.invalid:
                    self.delay=1
                if event.key==kontrole[0][7] and self.igr.za_koga==2 and self.delay==0 and self.img1=="data/images/nogica1.png" and not self.igr.bot and not self.igr.invalid:
                    self.delay=1

        if(self.igr.za_koga==2):self.pos.x=self.igr.rect.left-7
        if(self.igr.za_koga==1):self.pos.x=self.igr.rect.right+7
        self.pos.y=self.igr.pos.y+self.igr.radius/7
        self.rect=self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        gran=2
        if(self.igr.radius==igrac_radius_mid):gran=7
        if(self.igr.radius==igrac_radius_max):gran=9

        if(self.igr.bot and EXPO_TOP1_HARD_AI):
            # IA difícil: patea antes y con menos demora de reacción.
            br=max(8, round(self.igr.radius/4))
        else:
            br=random.randrange(1, gran)

        for lopta in loptaa:
            if(self.igr.za_koga==2 and self.rect.left-lopta.rect.right<=br and lopta.pos.x<=self.igr.pos.x and self.rect.top-lopta.rect.bottom<=2 and self.delay==0 and self.igr.bot and self.img1=="data/images/nogica1.png" and not self.igr.invalid):self.delay=1
            if(self.igr.za_koga==1 and lopta.rect.left-self.rect.right<=br and lopta.pos.x>=self.igr.pos.x and self.rect.top-lopta.rect.bottom<=2 and self.delay==0 and self.igr.bot and self.img1=="data/images/nogica1.png" and not self.igr.invalid):self.delay=1

        self.pos=vec(self.igr.rect.midbottom)
        self.pos.y+=self.vis/7
        self.rect=self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        
        if(self.delay==12):
            self.delay=0
            if(self.igr.za_koga==1):self.image=pygame.transform.rotate(self.image,-90)
            else:self.image=pygame.transform.rotate(self.image,90)
        
        if(self.delay==0):
            self.pos=vec(self.igr.rect.midbottom)
            self.pos.y+=self.vis/7
        else:
            if(self.igr.za_koga==1 and self.delay==1):self.image=pygame.transform.rotate(self.image,90)
            elif(self.igr.za_koga==2 and self.delay==1):self.image=pygame.transform.rotate(self.image,-90)
            if(self.igr.za_koga==1):self.pos.x=self.igr.rect.right+7
            else:self.pos.x=self.igr.rect.left-7
            self.pos.y=self.igr.pos.y+self.igr.radius/7
            self.delay+=1
        
        self.rect=self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        self.rect.center=self.pos
        
    def update_col(self, nogica_image1, igrac_radius_mid, igrac_radius_max, granice_udarca, loptaa, sutnuo1, sutnuo2, lista_abilitija):

        prov=[]
        jel_prom=False
        jel_dodir_zvuk=0
        koja=0
        if(self.igr.radius==igrac_radius_mid):koja=1
        if(self.igr.radius==igrac_radius_max):koja=2

        if(self.delay>2):
            if(self.igr.za_koga==1 and self.delay>4):sutnuo1=False
            if(self.igr.za_koga==2 and self.delay>4):sutnuo2=False
            return (sutnuo1, sutnuo2, prov, jel_prom, jel_dodir_zvuk)

        ability1, ability2 = 0, 0
        for ability in lista_abilitija:
            if(ability.vrsta==2 and ability.igrac.za_koga==1):ability1=ability
            if(ability.vrsta==2 and ability.igrac.za_koga==2):ability2=ability

        for lopta in loptaa:
            if(self.rect.top-lopta.rect.bottom>2):continue
            if(lopta.iz_topa_sam==2):continue

            if(self.igr.za_koga==1):
                if(lopta.rect.left-self.rect.right>granice_udarca[koja][0]):continue
                if(lopta.pos.x<self.igr.pos.x):continue
                if(lopta.rect.top-self.igr.rect.bottom>granice_udarca[koja][5]):continue
                
                if(lopta.rect.left-self.igr.rect.right>granice_udarca[koja][1] or lopta.pos.y>self.igr.rect.bottom):
                    lopta.vel.x=25
                    lopta.vel.y=-5
                elif(lopta.rect.left-self.igr.rect.right>granice_udarca[koja][2]):
                    lopta.vel.x=20
                    lopta.vel.y=-10
                elif(lopta.rect.left-self.igr.rect.right>granice_udarca[koja][3]):
                    lopta.vel.x=15
                    lopta.vel.y=-13
                elif(lopta.rect.left-self.igr.rect.right>granice_udarca[koja][4]):
                    lopta.vel.x=10
                    lopta.vel.y=-16
                else:
                    lopta.vel.x=5
                    lopta.vel.y=-19

                if(lopta.iz_topa_sam==1):lopta.iz_topa_sam=0

                if(not ability1==0):
                    ability1.iskoristio=True
                    if(not lopta.bomba_sam[1]==0):jel_prom=True
                    lopta.bomba_sam[0]=1
                    lopta.bomba_sam[1]=self.igr
                
                sutnuo1=lopta.koja_sam+1
                prov.append(lopta)

                lopta.zadnji_diro=self.igr
            else:
                if(self.rect.left-lopta.rect.right>granice_udarca[koja][0]):continue
                if(lopta.pos.x>self.igr.pos.x):continue
                if(lopta.rect.top-self.igr.rect.bottom>granice_udarca[koja][5]):continue

                if(self.igr.rect.left-lopta.rect.right>granice_udarca[koja][1] or lopta.pos.y>self.igr.rect.bottom):
                    lopta.vel.x=-25
                    lopta.vel.y=-5
                elif(self.igr.rect.left-lopta.rect.right>granice_udarca[koja][2]):
                    lopta.vel.x=-20
                    lopta.vel.y=-10
                elif(self.igr.rect.left-lopta.rect.right>granice_udarca[koja][3]):
                    lopta.vel.x=-15
                    lopta.vel.y=-13
                elif(self.igr.rect.left-lopta.rect.right>granice_udarca[koja][4]):
                    lopta.vel.x=-10
                    lopta.vel.y=-16
                else:
                    lopta.vel.x=-5
                    lopta.vel.y=-19

                if(lopta.iz_topa_sam==1):lopta.iz_topa_sam=0

                if(not ability2==0):
                    ability2.iskoristio=True
                    if(not lopta.bomba_sam[1]==0):jel_prom=True
                    lopta.bomba_sam[0]=1
                    lopta.bomba_sam[1]=self.igr
                
                sutnuo2=lopta.koja_sam+1
                prov.append(lopta)

                lopta.zadnji_diro=self.igr

            jel_dodir_zvuk=1

        return (sutnuo1, sutnuo2, prov, jel_prom, jel_dodir_zvuk)
