import pygame
import math
import copy
vec=pygame.math.Vector2

imageovi=[]
for i in range(45):
    imageovi.append(pygame.image.load("data/images/oblik4_"+str(i)+".png"))

class PokretniTeren(pygame.sprite.Sprite):
    def __init__(self, pos, sirina, visina, koji, omjer, grupa, rotation):
        super(PokretniTeren, self).__init__()
        self.pos=vec(pos)*omjer
        self.koji=koji
        self.sir=sirina*omjer
        self.vis=visina*omjer
        self.radius=self.sir/2
        self.masa=100
        self.vel=vec(0,0)
        self.grupa=grupa
        self.has_rotation_point=rotation[0]
        self.rotation_point_pos=rotation[1]
        self.rotation_speed=rotation[2]
        if(isinstance(koji, tuple)):
            self.koji=koji[0]
            self.osobine=koji[1]
        else:self.koji=koji
        
        if self.koji==5 or self.koji==6:
            self.org_pos=copy.deepcopy(self.pos)
            if(self.koji==5):self.mod=1
            else:self.mod=-1
            self.brzina_rotacije=self.osobine[0]
            self.masa=100
            self.stanje=0
            self.img=imageovi
            self.radius=13*(self.sir/imageovi[self.stanje].get_width())
            self.image=pygame.transform.smoothscale(self.img[self.stanje], (self.sir, self.vis)).convert_alpha()
            self.rect=self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
            #gore, desno, dolje, lijevo
            self.v21=vec(self.pos.x+(self.sir/2-self.radius)*math.cos(math.radians(90-self.stanje*2)), self.pos.y-(self.vis/2-self.radius)*math.sin(math.radians(90-self.stanje*2)))
            self.v22=vec(self.pos.x+(self.sir/2-self.radius)*math.cos(math.radians(360-self.stanje*2)), self.pos.y-(self.vis/2-self.radius)*math.sin(math.radians(360-self.stanje*2)))
            self.v23=vec(self.pos.x+(self.sir/2-self.radius)*math.cos(math.radians(270-self.stanje*2)), self.pos.y-(self.vis/2-self.radius)*math.sin(math.radians(270-self.stanje*2)))
            self.v24=vec(self.pos.x+(self.sir/2-self.radius)*math.cos(math.radians(180-self.stanje*2)), self.pos.y-(self.vis/2-self.radius)*math.sin(math.radians(180-self.stanje*2)))

            self.mjerne_tocke=[]
            self.mjerne_tocke.append(vec(self.v21.x+self.radius*math.sin(math.radians(90-self.stanje*2)), self.v21.y+self.radius*math.cos(math.radians(90-self.stanje*2))))
            self.mjerne_tocke.append(vec(self.v21.x-self.radius*math.sin(math.radians(90-self.stanje*2)), self.v21.y-self.radius*math.cos(math.radians(90-self.stanje*2))))
            self.mjerne_tocke.append(vec(self.v22.x+self.radius*math.sin(math.radians(360-self.stanje*2)), self.v22.y+self.radius*math.cos(math.radians(360-self.stanje*2))))
            self.mjerne_tocke.append(vec(self.v22.x-self.radius*math.sin(math.radians(360-self.stanje*2)), self.v22.y-self.radius*math.cos(math.radians(360-self.stanje*2))))
            self.mjerne_tocke.append(vec(self.v23.x+self.radius*math.sin(math.radians(270-self.stanje*2)), self.v23.y+self.radius*math.cos(math.radians(270-self.stanje*2))))
            self.mjerne_tocke.append(vec(self.v23.x-self.radius*math.sin(math.radians(270-self.stanje*2)), self.v23.y-self.radius*math.cos(math.radians(270-self.stanje*2))))
            self.mjerne_tocke.append(vec(self.v24.x+self.radius*math.sin(math.radians(180-self.stanje*2)), self.v24.y+self.radius*math.cos(math.radians(180-self.stanje*2))))
            self.mjerne_tocke.append(vec(self.v24.x-self.radius*math.sin(math.radians(180-self.stanje*2)), self.v24.y-self.radius*math.cos(math.radians(180-self.stanje*2))))
            
            self.vel_org=(2*3.142*(self.sir-self.radius))/(3/self.brzina_rotacije*60)
            if(self.mod==1):
                self.vel1=vec(self.vel_org*math.sin(math.radians(90-self.stanje*2)), self.vel_org*math.cos(math.radians(90-self.stanje*2)))
                self.vel2=vec(self.vel_org*math.sin(math.radians(360-self.stanje*2)), self.vel_org*math.cos(math.radians(360-self.stanje*2)))
                self.vel3=vec(self.vel_org*math.sin(math.radians(270-self.stanje*2)), self.vel_org*math.cos(math.radians(270-self.stanje*2)))
                self.vel4=vec(self.vel_org*math.sin(math.radians(180-self.stanje*2)), self.vel_org*math.cos(math.radians(180-self.stanje*2)))
            else:
                self.vel1=vec(self.vel_org*math.sin(math.radians(270-self.stanje*2)), self.vel_org*math.cos(math.radians(270-self.stanje*2)))
                self.vel2=vec(self.vel_org*math.sin(math.radians(180-self.stanje*2)), self.vel_org*math.cos(math.radians(180-self.stanje*2)))
                self.vel3=vec(self.vel_org*math.sin(math.radians(90-self.stanje*2)), self.vel_org*math.cos(math.radians(90-self.stanje*2)))
                self.vel4=vec(self.vel_org*math.sin(math.radians(360-self.stanje*2)), self.vel_org*math.cos(math.radians(360-self.stanje*2)))
        elif(self.koji==7):
            self.pos2=vec(self.osobine[0])
            self.org_pos=copy.deepcopy(self.pos)
            self.org_pos2=copy.deepcopy(self.pos2)
            self.masa=self.osobine[1]
            self.gravitacija=self.osobine[2]
            self.boja=self.osobine[3]
            self.postavi_njihalo()

    def update_rotation(self, factor1, factor2):
        #factor1 --> -1 kad trebamo vracat za collision, 1 za normalni rad
        #factor2 --> kolko je umanjen korak vracanja za collision

        if(not self.has_rotation_point):return

        if(self.koji==5 or self.koji==6):
            pos_pom=self.pos-self.rotation_point_pos
            pos_pom=pos_pom.rotate(factor1*self.rotation_speed/factor2)
            self.pos=self.rotation_point_pos+pos_pom
            self.rect=self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        elif(self.koji==7):
            stari_pos2=copy.deepcopy(self.pos2)
            pos_pom=self.pos2-self.rotation_point_pos
            pos_pom=pos_pom.rotate(factor1*self.rotation_speed/factor2)
            self.pos2=self.rotation_point_pos+pos_pom
            self.pos+=self.pos2-stari_pos2

    def update1(self):
        self.stanje+=1*self.mod*self.brzina_rotacije
        if(self.stanje>=len(self.img)):self.stanje=self.stanje-len(self.img)
        elif(self.stanje<0):self.stanje=self.stanje+len(self.img)
        self.image=pygame.transform.smoothscale(self.img[self.stanje],(self.sir, self.vis)).convert_alpha()
        self.rect=self.image.get_rect(center=(round(self.pos.x),round(self.pos.y)))
        self.v21=vec(self.pos.x+(self.sir/2-self.radius)*math.cos(math.radians(90-self.stanje*2)),self.pos.y-(self.vis/2-self.radius)*math.sin(math.radians(90-self.stanje*2)))
        self.v22=vec(self.pos.x+(self.sir/2-self.radius)*math.cos(math.radians(360-self.stanje*2)),self.pos.y-(self.vis/2-self.radius)*math.sin(math.radians(360-self.stanje*2)))
        self.v23=vec(self.pos.x+(self.sir/2-self.radius)*math.cos(math.radians(270-self.stanje*2)),self.pos.y-(self.vis/2-self.radius)*math.sin(math.radians(270-self.stanje*2)))
        self.v24=vec(self.pos.x+(self.sir/2-self.radius)*math.cos(math.radians(180-self.stanje*2)),self.pos.y-(self.vis/2-self.radius)*math.sin(math.radians(180-self.stanje*2)))

        self.mjerne_tocke=[]
        self.mjerne_tocke.append(vec(self.v21.x+self.radius*math.sin(math.radians(90-self.stanje*2)), self.v21.y+self.radius*math.cos(math.radians(90-self.stanje*2))))
        self.mjerne_tocke.append(vec(self.v21.x-self.radius*math.sin(math.radians(90-self.stanje*2)), self.v21.y-self.radius*math.cos(math.radians(90-self.stanje*2))))
        self.mjerne_tocke.append(vec(self.v22.x+self.radius*math.sin(math.radians(360-self.stanje*2)), self.v22.y+self.radius*math.cos(math.radians(360-self.stanje*2))))
        self.mjerne_tocke.append(vec(self.v22.x-self.radius*math.sin(math.radians(360-self.stanje*2)), self.v22.y-self.radius*math.cos(math.radians(360-self.stanje*2))))
        self.mjerne_tocke.append(vec(self.v23.x+self.radius*math.sin(math.radians(270-self.stanje*2)), self.v23.y+self.radius*math.cos(math.radians(270-self.stanje*2))))
        self.mjerne_tocke.append(vec(self.v23.x-self.radius*math.sin(math.radians(270-self.stanje*2)), self.v23.y-self.radius*math.cos(math.radians(270-self.stanje*2))))
        self.mjerne_tocke.append(vec(self.v24.x+self.radius*math.sin(math.radians(180-self.stanje*2)), self.v24.y+self.radius*math.cos(math.radians(180-self.stanje*2))))
        self.mjerne_tocke.append(vec(self.v24.x-self.radius*math.sin(math.radians(180-self.stanje*2)), self.v24.y-self.radius*math.cos(math.radians(180-self.stanje*2))))
     
        if(self.mod==1):
            self.vel1=vec(self.vel_org*math.sin(math.radians(90-self.stanje*2)), self.vel_org*math.cos(math.radians(90-self.stanje*2)))
            self.vel2=vec(self.vel_org*math.sin(math.radians(360-self.stanje*2)), self.vel_org*math.cos(math.radians(360-self.stanje*2)))
            self.vel3=vec(self.vel_org*math.sin(math.radians(270-self.stanje*2)), self.vel_org*math.cos(math.radians(270-self.stanje*2)))
            self.vel4=vec(self.vel_org*math.sin(math.radians(180-self.stanje*2)), self.vel_org*math.cos(math.radians(180-self.stanje*2)))
        else:
            self.vel1=vec(self.vel_org*math.sin(math.radians(270-self.stanje*2)), self.vel_org*math.cos(math.radians(270-self.stanje*2)))
            self.vel2=vec(self.vel_org*math.sin(math.radians(180-self.stanje*2)), self.vel_org*math.cos(math.radians(180-self.stanje*2)))
            self.vel3=vec(self.vel_org*math.sin(math.radians(90-self.stanje*2)), self.vel_org*math.cos(math.radians(90-self.stanje*2)))
            self.vel4=vec(self.vel_org*math.sin(math.radians(360-self.stanje*2)), self.vel_org*math.cos(math.radians(360-self.stanje*2)))
        self.vel=0

    def update2(self):
        self.pos1=copy.deepcopy(self.pos)
        self.vel1=copy.deepcopy(self.vel)
        self.pos.x=self.pos2.x+self.raz_sir*math.sin(self.kutna_brzina*self.vrijeme+math.radians(self.pom))
        self.kut=self.max_kut*math.sin(self.kutna_brzina*self.vrijeme+math.radians(self.pom))
        self.pos.y=self.pos2.y+math.sqrt(self.duljina*self.duljina-(self.pos.x-self.pos2.x)*(self.pos.x-self.pos2.x))
        self.vrijeme+=1
        self.pot_energija=self.masa*self.gravitacija*(self.pos2.y+self.duljina-self.pos.y)
        vel=math.sqrt((abs(self.uk_energija-self.pot_energija))*2/self.masa)
        self.vel.x=math.cos(abs(self.kut))*vel
        self.vel.y=math.sin(abs(self.kut))*vel
        if(self.pos1.x>self.pos.x):self.vel.x*=-1
        if(self.pos1.y>self.pos.y):self.vel.y*=-1
        #if(self.vrijeme==203):self.vrijeme=0

    def postavi_njihalo(self):
        self.duljina=self.pos.distance_to(self.pos2)
        self.raz_vis=self.pos2.y+self.duljina-self.pos.y
        self.raz_sir=abs(self.pos2.x-self.pos.x)
        self.uk_energija=self.masa*self.gravitacija*self.raz_vis
        self.kutna_brzina=math.sqrt(self.gravitacija/self.duljina)
        self.max_kut=math.asin(self.raz_sir/self.duljina)
        self.vel=vec(0,0)
        #self.pomak_kod_sudara=-1
        if(self.pos.x<=self.pos2.x):
            self.vrijeme=0
            self.pom=270
        else:
            self.vrijeme=0
            self.pom=90

    def za_njihalo(self, ozn, factor):
        if(ozn==1):self.vrijeme+=1/factor
        self.pos.x=self.pos2.x+self.raz_sir*math.sin(self.kutna_brzina*self.vrijeme+math.radians(self.pom))
        self.pos.y=self.pos2.y+math.sqrt(self.duljina*self.duljina-(self.pos.x-self.pos2.x)*(self.pos.x-self.pos2.x))
        self.kut=self.max_kut*math.sin(self.kutna_brzina*self.vrijeme+math.radians(self.pom))
        self.pot_energija=self.masa*self.gravitacija*(self.pos2.y+self.duljina-self.pos.y)
        vel=math.sqrt((abs(self.uk_energija-self.pot_energija))*2/self.masa)
        self.vel.x=math.cos(abs(self.kut))*vel
        self.vel.y=math.sin(abs(self.kut))*vel
        if(self.pos1.x>self.pos.x):self.vel.x*=-1
        if(self.pos1.y>self.pos.y):self.vel.y*=-1

    def calculate_velocity(self):
        if(self.koji==5 or self.koji==6):pos=self.pos
        elif(self.koji==7):pos=self.pos2
        
        dist=self.rotation_point_pos.distance_to(pos)
        speed=2*dist*math.pi*abs(self.rotation_speed)/6/60
        r=pos-self.rotation_point_pos
        r=r.normalize()
        if(self.rotation_speed>0):r=r.rotate(90)
        else:r=r.rotate(-90)
        return speed*r

    def render(self, surf):
        if(self.koji==5 or self.koji==6):
            surf.blit(self.image, self.rect)
        elif(self.koji==7):
            pygame.draw.line(surf, self.boja, self.pos, self.pos2, 2)
            pygame.draw.circle(surf, self.boja, self.pos, self.sir/2)

    def postavi(self):
        if(self.koji==7):
            self.pos=copy.deepcopy(self.org_pos)
            self.pos2=copy.deepcopy(self.org_pos2)
            self.postavi_njihalo()
        else:
            self.pos=copy.deepcopy(self.org_pos)
            self.stanje=0
            self.image=pygame.transform.smoothscale(self.img[self.stanje],(self.sir, self.vis)).convert_alpha()
            self.rect=self.image.get_rect(center=(round(self.pos.x),round(self.pos.y)))



        
