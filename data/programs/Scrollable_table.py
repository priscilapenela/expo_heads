import pygame
import math
import copy
vec=pygame.math.Vector2

scroll_color1=(12, 178, 59)
#scroll_color2=(87, 223, 125)
scroll_color2=(39, 214, 88)
scroll_color3=(98, 225, 134)
scroll_color4=(173, 240, 191)

class Scrollable_table(pygame.sprite.Sprite):
    def __init__(self, max_width, max_height, pos_topleft, num_of_columns, table_color, text_color, text_font, text_size1, text_size2, bold1, bold2, column_breakers, dist_from_breaker, scroll1_width, scroll2_height, row_height, row0_height, has_scroll1, has_scroll2, row0_content, content, main_lines_width, other_lines_width, selected_lines_color):
        super(Scrollable_table, self).__init__()
        self.max_width=max_width                                    #sirina cijele tablice
        self.max_height=max_height                                  #visina cijele tablice
        self.pos=vec(pos_topleft)                                   #pozicija tablice na ekranu (gornji lijevi kut)
        self.num_of_columns=num_of_columns                          #broj stupaca
        self.table_color=table_color                                #boja rešetke
        self.text_color=text_color                                  #boja teksta
        self.text_font1=pygame.font.SysFont(text_font, text_size1, bold=bold1, italic=False)
        self.text_font2=pygame.font.SysFont(text_font, text_size2, bold=bold2, italic=False)
        self.column_breakers=column_breakers                        #lista pozicija stupaca rešetke
        self.dist_from_breaker=dist_from_breaker                    #udaljenost teksta u retku od stupca rešetke
        self.scroll1_max_width=copy.deepcopy(scroll1_width)         #sirina scrolla desnog
        self.scroll1_max_height=0                                   #visina scrolla desnog
        self.scroll2_max_width=0                                    #sirina scrolla donjeg
        self.scroll2_max_height=copy.deepcopy(scroll2_height)       #visina scrolla donjeg
        self.row_height=row_height                                  #visina retka
        self.row0_height=row0_height                                #visina naslovnog retka
        self.has_scroll1=has_scroll1                                #postoji li desni scroll
        self.has_scroll2=has_scroll2                                #postoji li donji scroll
        self.row0_content=row0_content
        self.content=copy.deepcopy(content)
        self.main_lines_width=main_lines_width
        self.other_lines_width=other_lines_width
        self.selected_lines_color=selected_lines_color

        if(self.has_scroll2):
            self.scroll1_max_height=copy.deepcopy(self.max_height-self.scroll2_max_height-self.row0_height)
            self.scroll2_max_width=copy.deepcopy(self.max_width-self.scroll1_max_width)
        else:
            self.scroll1.max_height=copy.deepcopy(self.max_height-self.row0_height)

        self.scroll1_height=self.scroll1_max_height
        self.scroll1_width=self.scroll1_max_width
        self.scroll2_height=self.scroll2_max_height
        self.scroll2_width=self.scroll2_max_width

        self.content_max_width=copy.deepcopy(self.max_width-self.scroll1_width)
        self.content_max_height=copy.deepcopy(self.max_height-self.scroll2_height-self.row0_height)
        self.scroll1_pos=vec(self.pos.x+self.content_max_width, self.pos.y+self.row0_height)
        self.scroll2_pos=vec(self.pos.x, self.pos.y+self.content_max_height+self.row0_height)
        self.showing_pos=vec(0,0)                   #pozicija u podacima (gornji lijevi kut)
        self.content_height=0
        self.content_width=self.column_breakers[len(self.column_breakers)-1]

        self.scroll1_min_pos=copy.deepcopy(self.scroll1_pos)
        self.scroll2_min_pos=copy.deepcopy(self.scroll2_pos)
        self.scroll1_max_pos=copy.deepcopy(self.scroll1_pos)
        self.scroll2_max_pos=copy.deepcopy(self.scroll2_pos)
        
        self.scroll1_color=scroll_color4
        self.scroll2_color=scroll_color4
        self.scroll1_pressed=False
        self.scroll2_pressed=False
        self.prev_mouse_pos=(-1, -1)

        self.row_selected=-1

        self.update_scroll_size()

    def setup(self):
        self.row_selected=-1
        self.content=[]
        self.content_height=0
        self.update_scroll_size()

    def add_content(self, content=None):
        if(len(self.content)==0):novi_pos=vec(0,self.row0_height)
        else:novi_pos=self.content[len(self.content)-1][0]+vec(0, self.row_height)
        self.content.append([novi_pos, content])
        self.content_height+=self.row_height
        self.update_scroll_size()

    def remove_content(self, pos):
        self.content.pop(pos)
        for i in range(pos, len(self.content)):
            self.content[i][0].y-=self.row_height
        self.content_height-=self.row_height
        self.update_scroll_size()

        if(self.row_selected==pos):self.row_selected=-1
        elif(self.row_selected>pos):self.row_selected-=1

    def update_showing_pos(self):
        if(self.has_scroll1):
            if(self.scroll1_pos.y==self.scroll1_min_pos.y):self.showing_pos.y=0
            else:self.showing_pos.y=(self.scroll1_pos.y-self.scroll1_min_pos.y)/(self.scroll1_max_pos.y-self.scroll1_min_pos.y)*(self.content_height-self.content_max_height)

        if(self.has_scroll2):
            if(self.scroll2_pos.x==self.scroll2_min_pos.x):self.showing_pos.x=0
            else:self.showing_pos.x=(self.scroll2_pos.x-self.scroll2_min_pos.x)/(self.scroll2_max_pos.x-self.scroll2_min_pos.x)*(self.content_width-self.content_max_width)
    
    def update_scroll_size(self):
        if(self.has_scroll1):
            if(self.content_height<=self.content_max_height):self.scroll1_height=self.scroll1_max_height
            else:self.scroll1_height=(self.content_max_height/self.content_height)*self.scroll1_max_height
            self.scroll1_max_pos.y=self.scroll1_min_pos.y+(self.scroll1_max_height-self.scroll1_height)
            if(self.scroll1_pos.y>self.scroll1_max_pos.y):self.scroll1_pos.y=self.scroll1_max_pos.y
            
        if(self.has_scroll2):
            if(self.content_width<=self.content_max_width):self.scroll2_width=self.scroll2_max_width
            else:self.scroll2_width=(self.content_max_width/self.content_width)*self.scroll2_max_width       
            self.scroll2_max_pos.x=self.scroll2_min_pos.x+(self.scroll2_max_width-self.scroll2_width)
            if(self.scroll2_pos.x>self.scroll2_max_pos.x):self.scroll2_pos.x=self.scroll2_max_pos.x

    def update_scroll(self, mouse_pos, mouse_press, mouse_wheel, arrow_press):
        if(self.has_scroll1):
            if(self.is_mouse_on_scroll(mouse_pos, 1) or (self.scroll1_pressed and mouse_press[0])):
                if(mouse_press[0]):
                    self.scroll1_color=scroll_color1
                    if(self.scroll1_pressed):
                        self.scroll1_pos.y+=(mouse_pos[1]-self.prev_mouse_pos[1])
                        self.scroll1_pos.y=min(self.scroll1_max_pos.y, self.scroll1_pos.y)
                        self.scroll1_pos.y=max(self.scroll1_min_pos.y, self.scroll1_pos.y)
                    else:self.scroll1_pressed=True
                    self.prev_mouse_pos=mouse_pos
                else:
                    self.scroll1_color=scroll_color2
                    self.scroll1_pressed=False
                    self.prev_mouse_pos=(-1, -1)
            else:
                self.scroll1_color=scroll_color3
                self.scroll1_pressed=False

            if(not mouse_wheel==0):
                if(mouse_wheel==1):self.scroll1_pos.y-=20
                else:self.scroll1_pos.y+=20
                self.scroll1_pos.y=min(self.scroll1_max_pos.y, self.scroll1_pos.y)
                self.scroll1_pos.y=max(self.scroll1_min_pos.y, self.scroll1_pos.y)

        if(self.has_scroll2):
            if(self.is_mouse_on_scroll(mouse_pos, 2) or (self.scroll2_pressed and mouse_press[0])):
                if(mouse_press[0]):
                    self.scroll2_color=scroll_color1
                    if(self.scroll2_pressed):
                        self.scroll2_pos.x+=(mouse_pos[0]-self.prev_mouse_pos[0])
                        self.scroll2_pos.x=min(self.scroll2_max_pos.x, self.scroll2_pos.x)
                        self.scroll2_pos.x=max(self.scroll2_min_pos.x, self.scroll2_pos.x)
                    else:self.scroll2_pressed=True
                    self.prev_mouse_pos=mouse_pos
                else:
                    self.scroll2_color=scroll_color2
                    self.scroll2_pressed=False
                    self.prev_mouse_pos=(-1, -1)
            else:
                self.scroll2_color=scroll_color3
                self.scroll2_pressed=False

            if(arrow_press[0] or arrow_press[1]):
                if(arrow_press[0]):self.scroll2_pos.x-=20
                else:self.scroll2_pos.x+=20
                self.scroll2_pos.x=min(self.scroll2_max_pos.x, self.scroll2_pos.x)
                self.scroll2_pos.x=max(self.scroll2_min_pos.x, self.scroll2_pos.x)


        return self.scroll1_pressed or self.scroll2_pressed
                
                        
    def is_mouse_on_scroll(self, mouse_pos, koji):
        if(koji==1):
            if(mouse_pos[0]>=self.scroll1_pos.x and mouse_pos[0]<=self.scroll1_pos.x+self.scroll1_width
               and mouse_pos[1]>=self.scroll1_pos.y and mouse_pos[1]<=self.scroll1_pos.y+self.scroll1_height):
                return True
            else:
                return False
        else:
            if(mouse_pos[0]>=self.scroll2_pos.x and mouse_pos[0]<=self.scroll2_pos.x+self.scroll2_width
               and mouse_pos[1]>=self.scroll2_pos.y and mouse_pos[1]<=self.scroll2_pos.y+self.scroll2_height):
                return True
            else:
                return False

    def update_scroll_after_arrow_move(self):
        pos=self.content[self.row_selected][0]
        if(self.pos.y+pos.y-self.showing_pos.y<self.pos.y+self.row0_height):
            self.scroll1_pos.y-=(((self.pos.y+self.row0_height)-(self.pos.y+pos.y-self.showing_pos.y))/(self.content_height-self.content_max_height))*(self.scroll1_max_height-self.scroll1_height)
            self.update_showing_pos()
            self.update_scroll_size()
        elif(self.pos.y+pos.y+self.row_height-self.showing_pos.y>self.pos.y+self.max_height-self.scroll2_height):
            self.scroll1_pos.y+=(((self.pos.y+pos.y+self.row_height-self.showing_pos.y)-(self.pos.y+self.max_height-self.scroll2_height))/(self.content_height-self.content_max_height))*(self.scroll1_max_height-self.scroll1_height)
            self.update_showing_pos()
            self.update_scroll_size()

    def check_row_press(self, mouse_pos, mouse_press, arrow_press, is_any_button_pressed):
        if(not self.row_selected==-1 and arrow_press[0]):
            self.row_selected=max(0, self.row_selected-1)
            self.update_scroll_after_arrow_move()
        if(not self.row_selected==-1 and arrow_press[1]):
            self.row_selected=min(len(self.content)-1, self.row_selected+1)
            self.update_scroll_after_arrow_move()
        
        if(not (mouse_pos[0]>=self.pos.x and mouse_pos[0]<=self.pos.x+self.content_max_width and mouse_pos[1]>=self.pos.y+self.row0_height and mouse_pos[1]<=self.pos.y+self.row0_height+self.content_max_height)):
            if(mouse_press[0] and not self.scroll1_pressed and not self.scroll2_pressed and not is_any_button_pressed):self.row_selected=-1
            return
        elif(not mouse_press[0] or self.scroll1_pressed or self.scroll2_pressed):
            return

        new_select=False
        for i in range(len(self.content)):
            pos=self.content[i][0]
            content=self.content[i][1]

            if(
                mouse_pos[0]>self.pos.x+pos.x-self.showing_pos.x and
                mouse_pos[0]<self.pos.x+self.content_max_width and
                mouse_pos[1]>self.pos.y+pos.y-self.showing_pos.y and
                mouse_pos[1]<self.pos.y+pos.y+self.row_height-self.showing_pos.y
            ):
                self.row_selected=i
                new_select=True

        if(not new_select):self.row_selected=-1

    def render(self, screen):
        if(self.has_scroll1):
            pygame.draw.polygon(screen, scroll_color4, [self.scroll1_min_pos, self.scroll1_min_pos+vec(0, self.scroll1_max_height), self.scroll1_min_pos+vec(self.scroll1_max_width, self.scroll1_max_height), self.scroll1_min_pos+vec(self.scroll1_max_width, 0)])
            pygame.draw.polygon(screen, self.scroll1_color, [self.scroll1_pos, self.scroll1_pos+vec(0, self.scroll1_height), self.scroll1_pos+vec(self.scroll1_width, self.scroll1_height), self.scroll1_pos+vec(self.scroll1_width, 0)])
        if(self.has_scroll2):
            pygame.draw.polygon(screen, scroll_color4, [self.scroll2_min_pos, self.scroll2_min_pos+vec(0, self.scroll2_max_height), self.scroll2_min_pos+vec(self.scroll2_max_width, self.scroll2_max_height), self.scroll2_min_pos+vec(self.scroll2_max_width, 0)])
            pygame.draw.polygon(screen, self.scroll2_color, [self.scroll2_pos, self.scroll2_pos+vec(0, self.scroll2_height), self.scroll2_pos+vec(self.scroll2_width, self.scroll2_height), self.scroll2_pos+vec(self.scroll2_width, 0)])

        for i in range(self.num_of_columns):
            if(self.pos.x+self.column_breakers[i+1]-self.showing_pos.x>self.pos.x and self.pos.x+self.column_breakers[i+1]-self.showing_pos.x<self.pos.x+self.max_width-self.scroll1_width):
                pygame.draw.line(screen, self.table_color, self.pos+vec(self.column_breakers[i+1]-self.showing_pos.x, 0), self.pos+vec(self.column_breakers[i+1]-self.showing_pos.x, self.max_height-self.scroll2_height-1))

            tekst=self.text_font1.render(self.row0_content[i], False, self.text_color)
            blit_pos=(
                max(self.pos.x+self.column_breakers[i]+self.dist_from_breaker-self.showing_pos.x, self.pos.x+self.dist_from_breaker),
                self.pos.y+self.row0_height/2-tekst.get_height()/2
            )
            area=(
                max(self.pos.x+self.dist_from_breaker-(self.pos.x+self.column_breakers[i]+self.dist_from_breaker-self.showing_pos.x), 0),
                0,
                tekst.get_width()+min((self.pos.x+self.content_max_width-self.dist_from_breaker)-(self.pos.x+self.column_breakers[i]+self.dist_from_breaker-self.showing_pos.x+tekst.get_width()), 0),
                tekst.get_height()
            )
            screen.blit(tekst, blit_pos, area)

        pygame.draw.line(screen, self.table_color, self.pos, self.pos+vec(self.max_width, 0), self.main_lines_width)
        pygame.draw.line(screen, self.table_color, self.pos+vec(0, self.row0_height), self.pos+vec(self.max_width, self.row0_height), self.main_lines_width)

        for j in range(len(self.content)):
            pos=self.content[j][0]
            content=self.content[j][1]
            if(self.pos.y+pos.y-self.showing_pos.y>self.pos.y+self.row0_height and self.pos.y+pos.y-self.showing_pos.y<self.pos.y+self.max_height-self.scroll2_height):
                pygame.draw.line(screen, self.table_color, self.pos+vec(0,pos.y-self.showing_pos.y), self.pos+vec(0,pos.y)+vec(self.content_max_width, 0)-vec(0,self.showing_pos.y)-vec(1,0), self.other_lines_width)

            for i in range(self.num_of_columns):            
                tekst=self.text_font2.render(content[i], False, self.text_color)
                blit_pos=(
                    max(self.pos.x+pos.x+self.column_breakers[i]+self.dist_from_breaker-self.showing_pos.x, self.pos.x+self.dist_from_breaker),
                    max(self.pos.y+pos.y+self.row_height/2-tekst.get_height()/2-self.showing_pos.y, self.pos.y+self.row0_height+self.row_height/2-tekst.get_height()/2)
                )
                area=(
                    max(self.pos.x+self.dist_from_breaker-(self.pos.x+pos.x+self.column_breakers[i]+self.dist_from_breaker-self.showing_pos.x), 0),
                    max((self.pos.y+self.row0_height+self.row_height/2-tekst.get_height()/2)-(self.pos.y+pos.y+self.row_height/2-tekst.get_height()/2-self.showing_pos.y),0),
                    tekst.get_width()+min((self.pos.x+self.content_max_width-self.dist_from_breaker)-(self.pos.x+self.column_breakers[i]+self.dist_from_breaker-self.showing_pos.x+tekst.get_width()), 0),
                    tekst.get_height()+min((self.pos.y+self.max_height-self.scroll2_height-self.row_height/2+tekst.get_height()/2)-(self.pos.y+pos.y+self.row_height/2+tekst.get_height()/2-self.showing_pos.y), 0)
                )
                screen.blit(tekst, blit_pos, area)

            if(j==len(self.content)-1):
                if(self.pos.y+pos.y+self.row_height-self.showing_pos.y>self.pos.y+self.row0_height and self.pos.y+self.row_height+pos.y-self.showing_pos.y<self.pos.y+self.max_height-self.scroll2_height):
                    pygame.draw.line(screen, self.table_color, self.pos+vec(0,pos.y+self.row_height-self.showing_pos.y), self.pos+vec(0,pos.y+self.row_height)+vec(self.content_max_width, 0)-vec(0,self.showing_pos.y)-vec(1,0), self.other_lines_width)

         
        pygame.draw.line(screen, self.table_color, self.pos, self.pos+vec(0, self.max_height), self.main_lines_width)
        pygame.draw.line(screen, self.table_color, self.pos+vec(0, self.max_height-self.scroll2_height), self.pos+vec(self.max_width, self.max_height-self.scroll2_height), self.main_lines_width)
        pygame.draw.line(screen, self.table_color, self.pos+vec(0, self.max_height), self.pos+vec(self.max_width, self.max_height), self.main_lines_width)
        pygame.draw.line(screen, self.table_color, self.pos+vec(self.max_width-self.scroll1_width, 0), self.pos+vec(self.max_width-self.scroll1_width, self.max_height) , self.main_lines_width)
        pygame.draw.line(screen, self.table_color, self.pos+vec(self.max_width, 0), self.pos+vec(self.max_width, self.max_height) , self.main_lines_width)

        if(not self.row_selected==-1):
            pos=self.content[self.row_selected][0]
            if(not(self.pos.y+pos.y+self.row_height-self.showing_pos.y<self.pos.y+self.row0_height or self.pos.y+pos.y-self.showing_pos.y>self.pos.y+self.max_height-self.scroll2_height)):
                offset=self.main_lines_width
                top=self.pos.y+pos.y-self.showing_pos.y
                bottom=self.pos.y+pos.y+self.row_height-self.showing_pos.y
                if(self.pos.y+pos.y-self.showing_pos.y<self.pos.y+self.row0_height):
                    top=self.pos.y+self.row0_height
                    pygame.draw.line(screen, self.selected_lines_color, vec(self.pos.x+offset, bottom), vec(self.pos.x+self.content_max_width-offset, bottom), self.main_lines_width)
                elif(self.pos.y+pos.y+self.row_height-self.showing_pos.y>self.pos.y+self.max_height-self.scroll2_height):
                    bottom=self.pos.y+self.max_height-self.scroll2_height
                    pygame.draw.line(screen, self.selected_lines_color, vec(self.pos.x+offset, top), vec(self.pos.x+self.content_max_width-offset, top), self.main_lines_width)
                else:
                    pygame.draw.line(screen, self.selected_lines_color, vec(self.pos.x+offset, bottom), vec(self.pos.x+self.content_max_width-offset, bottom), self.main_lines_width)
                    pygame.draw.line(screen, self.selected_lines_color, vec(self.pos.x+offset, top), vec(self.pos.x+self.content_max_width-offset, top), self.main_lines_width)

                pygame.draw.line(screen, self.selected_lines_color, vec(self.pos.x+offset, top), vec(self.pos.x+offset, bottom), self.main_lines_width)
                pygame.draw.line(screen, self.selected_lines_color, vec(self.pos.x+self.content_max_width-offset, top), vec(self.pos.x+self.content_max_width-offset, bottom), self.main_lines_width)
