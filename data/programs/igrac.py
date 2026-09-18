import pygame
import random
vec=pygame.math.Vector2

# -----------------------------------------------------------------------------
# EXPO HEADS - JOYSTICK CHECK 1
# P1 puede moverse a izquierda/derecha con el eje horizontal del primer mando.
# El teclado original sigue funcionando en paralelo.
# Salto y patada NO se modifican en este check.
# -----------------------------------------------------------------------------
JOYSTICK_DEADZONE = 0.35
_p1_joystick = None

def _p1_gamepad_axis_x():
    """Devuelve el eje X del joystick 1 o 0.0 si no hay mando disponible.

    Se inicializa de forma perezosa para no afectar el arranque del juego y para
    permitir conectar el mando incluso después de haber iniciado el proceso.
    """
    global _p1_joystick

    try:
        if not pygame.joystick.get_init():
            pygame.joystick.init()

        if _p1_joystick is None or not _p1_joystick.get_init():
            if pygame.joystick.get_count() < 1:
                return 0.0

            _p1_joystick = pygame.joystick.Joystick(0)
            _p1_joystick.init()
            print("[GAMEPAD] P1 detectado:", _p1_joystick.get_name())

        return _p1_joystick.get_axis(0)

    except pygame.error:
        # Si el mando se desconecta, volvemos al teclado y reintentamos luego.
        _p1_joystick = None
        return 0.0

igraci_image={}

for i in range(1,24,1):
    igraci_image["data/images/igrac"+str(i)+".png"]=pygame.image.load("data/images/igrac"+str(i)+".png")
igraci_image["data/images/robot.png"]=pygame.image.load("data/images/robot.png")

class Igrac1(pygame.sprite.Sprite):
    def __init__(self, pos, vel, acc, radius, koji, akc, skk, bot, image_igrac, za_koga, ability_bot, dodatno):
        super(Igrac1, self).__init__()
        self.pos=vec(pos)
        self.vel=vec(vel)
        self.acc=vec(acc)
        self.radius=radius
        self.koji=koji
        self.ACC=akc
        self.SKOK=skk
        self.bot=bot
        self.led=False
        self.invalid=0
        self.sudija=False
        self.masa=100
        self.ability_bot=ability_bot
        self.za_koga=za_koga
        self.nogica=0
        self.img=igraci_image[image_igrac]
        self.moj_image=image_igrac
        
        if(za_koga==1):self.img=pygame.transform.flip(self.img, True, False)

        self.image=pygame.transform.smoothscale(self.img, (self.radius*2, self.radius*2))
        self.rect=self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))        
        self.surface=pygame.Surface((self.radius*2, self.radius*2))
        self.surface.blit(self.image, self.rect)
        self.mask=pygame.mask.from_surface(self.image)

        if(len(dodatno)>0):
            self.led=dodatno[0]
            self.invalid=dodatno[1]
            self.sudija=dodatno[2]
            self.masa=dodatno[3]
    
    def update_move(self, stipke, koji, nogica1, sutnuo1, nogica2, sutnuo2, skok_zvuk, FRIC, kontrole, platforme, sirina, loptaa, poss, gravitacija, broj_lopti, gol_sirina, lista_igraca):
        jel_skok_zvuk=0

        # CHECK 1: solo movimiento horizontal del P1 con el stick izquierdo.
        # Eje 0 es el eje horizontal estándar en mandos Xbox/PlayStation vía SDL.
        p1_axis_x = _p1_gamepad_axis_x() if self.za_koga==1 and not self.bot else 0.0
        p1_gamepad_left = p1_axis_x < -JOYSTICK_DEADZONE
        p1_gamepad_right = p1_axis_x > JOYSTICK_DEADZONE
        if(self.invalid>0):
            self.invalid+=1
            if(self.invalid==300):
                self.invalid=0

        if(len(loptaa)==0):
            self.acc=vec(0,gravitacija+0.07)
            if(not self.invalid and not self.led and ((self.za_koga==2 and stipke[kontrole[0][4]] and not self.bot) or (self.za_koga==1 and not self.bot and (stipke[kontrole[0][0]] or p1_gamepad_left)))):
                self.acc.x = -self.ACC
            if(not self.invalid and not self.led and ((self.za_koga==2 and stipke[kontrole[0][5]] and not self.bot) or (self.za_koga==1 and not self.bot and (stipke[kontrole[0][1]] or p1_gamepad_right)))):
                self.acc.x = self.ACC
            if(not self.invalid and ((self.za_koga==2 and stipke[kontrole[0][6]] and not self.bot) or (self.za_koga==1 and not self.bot and stipke[kontrole[0][2]]))):
                hits = pygame.sprite.spritecollide(self, platforme, False)
                if hits:
                    if(not skok_zvuk==-1):jel_skok_zvuk=1
                    self.vel.y = -self.SKOK
            
            self.acc.x+=self.vel.x*FRIC
            self.vel+=self.acc
            self.pos+=self.vel+0.5*self.acc
            
            if self.rect.right>=sirina:
                self.acc.x*=-1
                self.vel.x*=-1
                self.pos.x=sirina-self.radius-1
            if self.rect.left<0:
                self.acc.x*=-1
                self.vel.x*=-1
                self.pos.x=self.radius+1
            
            self.rect.center = self.pos
            return jel_skok_zvuk

        minnp=1000000
        kojiminnp=0
        maxxp=0
        kojimaxxp=0
        for i in range(broj_lopti):
            if poss[i].x<minnp:
                minnp=poss[i].x
                kojiminnp=i
            if poss[i].x>maxxp:
                maxxp=poss[i].x
                kojimaxxp=i
            if loptaa[i].pos.x<minnp:
                minnp=loptaa[i].pos.x
                kojiminnp=i
            if loptaa[i].pos.x>maxxp:
                maxxp=loptaa[i].pos.x
                kojimaxxp=i

        kojip=0
        if(self.za_koga % 2 == 1):kojip=kojiminnp
        else:kojip=kojimaxxp

        lopta=loptaa[kojip]
        
        v1=vec(lopta.pos)
        v2=vec(self.pos)
        dist1=v1.distance_to(v2)
        br1=random.randrange(int(self.radius*2), 150)

        ok1=False
        for lopta in loptaa:
            if(lopta.pos.y<self.rect.top and dist1<=br1):ok1=True
            if(lopta.pos.y>self.pos.y and lopta.pos.x-self.pos.x<=75 and lopta.pos.x>self.pos.x):ok1=True

        #if(nogica1.delay>0 and sutnuo1 and loptaa[sutnuo1-1].vel.y<-7):
        if(nogica1.delay>0 and sutnuo1):
            br5=random.randrange(0,4)
            if(br5>0):ok1=True
            
        br2=random.randrange(round(self.radius/6), round(self.radius+20))

        v3=vec(lopta.pos)
        v4=vec(self.pos)
        dist2=v3.distance_to(v4)
        br3=random.randrange(int(self.radius*2), 150)
        
        ok2=False
        for lopta in loptaa:
            if(lopta.pos.y<self.rect.top and dist2<=br3):ok2=True
            if(lopta.pos.y>self.pos.y and self.pos.x-lopta.pos.x<=75 and lopta.pos.x<self.pos.x):ok2=True

        #if(nogica2.delay>0 and sutnuo2 and loptaa[sutnuo2-1].vel.y<-7):
        if(nogica2.delay>0 and sutnuo2):
            br5=random.randrange(0,4)
            if(br5>0):ok2=True
            
        br4=random.randrange(round(self.radius/6), round(self.radius+20))

        br6=random.randrange(round(self.radius/5), round(self.radius+10))
        nazad1,nazad2=False,False

        br7=random.randrange(round(self.radius/2), round(self.radius+15))

        if(self.za_koga==1 and poss[kojip].x-br6<self.pos.x):nazad1=True
        if(self.za_koga==2 and poss[kojip].x+br6>self.pos.x):nazad2=True

        ok3=False
        for igrac in lista_igraca:
            if(igrac.sudija or igrac==self or igrac.za_koga==self.za_koga or not self.bot):continue
            
            if(self.za_koga==1 and (self.vel.x<-2 or self.vel.x>2) and self.pos.distance_to(igrac.pos)<=self.radius+igrac.radius+3):ok3=True
            if(self.za_koga==2 and (self.vel.x<-2 or self.vel.x>2) and self.pos.distance_to(igrac.pos)<=self.radius+igrac.radius+3):ok3=True
            
        
        self.acc=vec(0,gravitacija+0.07)
        if (((self.za_koga==2 and ((stipke[kontrole[0][4]] and not self.bot) or (((lopta.pos.x<self.rect.left-br2 and not nazad2) or (self.pos.x>=sirina-gol_sirina+br7)) and self.bot))) or (self.za_koga==1 and (((stipke[kontrole[0][0]] or p1_gamepad_left) and not self.bot) or (((lopta.pos.x<self.pos.x-self.radius/4 or nazad1) and not (self.pos.x<gol_sirina-br7)) and self.bot)))) and  not self.led):
            if(not self.invalid):self.acc.x = -self.ACC
        if (((self.za_koga==2 and ((stipke[kontrole[0][5]] and not self.bot) or (((lopta.pos.x>self.pos.x+self.radius/4 or nazad2) and not (self.pos.x>sirina-gol_sirina+br7)) and self.bot))) or (self.za_koga==1 and (((stipke[kontrole[0][1]] or p1_gamepad_right) and not self.bot) or (((lopta.pos.x>self.rect.right+br4 and not nazad1) or (self.pos.x<=gol_sirina-br7)) and self.bot)))) and  not self.led):
            if(not self.invalid):self.acc.x = self.ACC

        
    
        if ((self.za_koga==2 and ((stipke[kontrole[0][6]] and not self.bot) or (ok1 and self.bot))) or (self.za_koga==1 and ((stipke[kontrole[0][2]] and not self.bot) or (ok2 and self.bot))) or (ok3 and self.bot)):
            
            hits = pygame.sprite.spritecollide(self, platforme, False)
            if hits:
                if(not skok_zvuk==-1 and not self.invalid):jel_skok_zvuk=1
                if(not self.invalid):self.vel.y = -self.SKOK

        if(not self.ability_bot==-1 and not self.led and not self.invalid):
            if(self.ability_bot.za_koga==1):
                if(self.ability_bot.pos.x>=sirina/4):
                    if(self.pos.x>=sirina/4):self.acc.x=-self.ACC
                    elif(poss[kojip].x-br6<self.rect.right and not (self.pos.x<gol_sirina-br7)):self.acc.x=-self.ACC
                    elif(poss[kojip].x-br6>=self.rect.right):self.acc.x=self.ACC
                else:
                    if(self.pos.x<=sirina/4):self.acc.x=self.ACC
                    elif(poss[kojip].x-br6>=self.rect.right):self.acc.x=self.ACC
                    elif(poss[kojip].x-br6<self.rect.right):self.acc.x=-self.ACC
                if(nogica1.delay>0 and sutnuo1):
                    self.vel.y=0
            if(self.ability_bot.za_koga==2):
                if(self.ability_bot.pos.x<=sirina-sirina/4):
                    if(self.pos.x<=sirina-sirina/4):self.acc.x=self.ACC
                    elif(poss[kojip].x+br6>self.rect.left and not (self.pos.x<gol_sirina-br7)):self.acc.x=self.ACC
                    elif(poss[kojip].x+br6<=self.rect.left):self.acc.x=-self.ACC
                else:
                    if(self.pos.x>=sirina-sirina/4):self.acc.x=-self.ACC
                    elif(poss[kojip].x+br6>=self.rect.left):self.acc.x=self.ACC
                    elif(poss[kojip].x+br6<self.rect.left):self.acc.x=-self.ACC
                if(nogica2.delay>0 and sutnuo2):
                    self.vel.y=0
            
                
        
        self.acc.x+=self.vel.x*FRIC
        self.vel+=self.acc
        self.pos+=self.vel+0.5*self.acc
        
        if self.rect.right>=sirina:
            self.acc.x*=-1
            self.vel.x*=-1
            self.pos.x=sirina-self.radius-1
        if self.rect.left<0:
            self.acc.x*=-1
            self.vel.x*=-1
            self.pos.x=self.radius+1
        
        self.rect.center = self.pos
        return jel_skok_zvuk

    def update_col(self, platforme):
        hits=pygame.sprite.spritecollide(self, platforme, False)
        if self.vel.y > 0:
            if hits:
                self.pos.y=hits[0].rect.top -self.radius+1
                self.vel.y=0

        self.rect.center = self.pos

    def update_ability(self, stipke, kontrole, koji):

        if(koji==1 and stipke[kontrole[0][8]]):return True
        if(koji==2 and stipke[kontrole[0][9]]):return True
        return False


        
