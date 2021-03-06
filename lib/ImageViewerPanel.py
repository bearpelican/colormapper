import wx
import os
import math

class ImageViewerPanel(wx.Panel):
    def __init__(self, parent, ID = -1, label = "",
                pos = wx.DefaultPosition, size = wx.DefaultSize):
        wx.Panel.__init__(self, parent, ID, pos, size,
                            wx.NO_BORDER, label)
                            
        # Default Parameters
        self.maintainAspectRatio = True
        self.dynamicResize = True
        self.resizeMethod = wx.IMAGE_QUALITY_HIGH
        # wxIMAGE_QUALITY_NEAREST: Simplest and fastest algorithm.
        # wxIMAGE_QUALITY_BILINEAR: Compromise between wxIMAGE_QUALITY_NEAREST and wxIMAGE_QUALITY_BICUBIC.
        # wxIMAGE_QUALITY_BICUBIC: Highest quality but slowest execution time.
        # wxIMAGE_QUALITY_BOX_AVERAGE: Use surrounding pixels to calculate an average that will be used for new pixels. This method is typically used when reducing the size of an image.
        # wxIMAGE_QUALITY_NORMAL: Default image resizing algorithm used by wxImage::Scale(). Currently the same as wxIMAGE_QUALITY_NEAREST.
        # wxIMAGE_QUALITY_HIGH: Best image resizing algorithm. Since version 2.9.2 this results in wxIMAGE_QUALITY_BOX_AVERAGE being used when reducing the size of the image (meaning that both the new width and height will be smaller than the original size). Otherwise wxIMAGE_QUALITY_BICUBIC is used.
        self.display_width = 1      # This is a temporary parameter
        self.display_height = 1     # This is a temporary parameter
        self.zoomFactor = 1.0       # This is a temporary parameter
        self.zoomFactorMax = 8.0
        self.zoomFactorMin = 1.0/self.zoomFactorMax
        self.zoomFactorIncreaseMultiplier = 1.05
        self.zoomFactorDecreaseMultiplier = 1.0/self.zoomFactorIncreaseMultiplier
        self.pos = (0,0)
        self.oldTranslation = (0,0)
        self.translation = (0,0)
        self.viewModes = [
            'Actual Size - no interaction',
            'Zoom to Fit - no interaction',
            'Zoom',
            'Pan']
        self.viewMode = 3
        self.SetBackgroundColour("Black")
        self.image = wx.Image() # Initialize with an empty image
        self.displayedImage = wx.Image()
        self.bmp = wx.Bitmap(1,1)
        self.newImageData = False
        self.drawCrosshair = False
        
        # Initialize Buffer
        self.InitBuffer()
        
        # Event handlers
        self.Bind(wx.EVT_SIZE, self.OnSize)       
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveWindow)
        # Mouse event handlers                
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        self.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        
    def OnLeaveWindow(self, event):
        self.InitBuffer()
        self.Refresh()
        

    def OnLeftDown(self, event):
        if self.viewMode == 3:
            self.pos = event.GetPosition()
            self.oldTranslation = self.translation
        self.CaptureMouse()     
        
    def OnLeftUp(self, event):
        if self.HasCapture():
            if self.viewMode == 0: 
                pass
            elif self.viewMode == 1: 
                pass
            elif self.viewMode == 2: 
                self.IncreaseZoomFactor()
                self.reInitBuffer = True
            elif self.viewMode == 3:
                self.reInitBuffer = True
            self.ReleaseMouse()
    

    def OnRightDown(self, event):
        self.CaptureMouse()

        
    def OnRightUp(self, event):
        if self.HasCapture():
            if self.viewMode == 0:
                pass
            elif self.viewMode == 1:
                pass
            elif self.viewMode == 2:
                self.DecreaseZoomFactor()
                self.reInitBuffer = True
            elif self.viewMode == 3:
                pass
            self.ReleaseMouse()
        
    def OnMotion(self, event):
        if self.viewMode == 3:
            if event.Dragging() and event.LeftIsDown():
                newPos = event.GetPosition()
                delta = (newPos[0] - self.pos[0], newPos[1] - self.pos[1])
                self.translation = (self.oldTranslation[0] + delta[0], self.oldTranslation[1] + delta[1])
                (view_width, view_height) = self.GetClientSize()
                if self.translation[0] > 0:
                    self.translation = (0, self.translation[1])
                if self.translation[0] < view_width - self.display_width:
                    self.translation = \
                        (view_width - self.display_width, self.translation[1])                    
                    
                if self.translation[1] > 0:
                    self.translation = (self.translation[0], 0)
                if self.translation[1] < view_height - self.display_height:
                    self.translation = \
                        (self.translation[0], view_height - self.display_height)
                self.reInitBuffer = True
                
        # Draw crosshairs if crosshairs are enabled
        if self.drawCrosshair:
            self.DrawCrosshair(event)
        event.Skip()
        
        
    def OnMouseWheel(self, event):
        if self.viewMode == 0:
            pass
        elif self.viewMode == 1:
            pass
        elif self.viewMode == 2 or self.viewMode == 3:
            x = event.GetWheelRotation()
            if x > 0:
                self.DecreaseZoomFactor()
                self.reInitBuffer = True
            elif x < 0:
                self.IncreaseZoomFactor()
                self.reInitBuffer = True
    

    def IncreaseZoomFactor(self):
        self.zoomFactor = self.zoomFactorIncreaseMultiplier*self.zoomFactor
        if self.zoomFactor > self.zoomFactorMax:
            self.zoomFactor = self.zoomFactorMax

    
    def DecreaseZoomFactor(self):
        self.zoomFactor = self.zoomFactorDecreaseMultiplier*self.zoomFactor
        if self.zoomFactor < self.zoomFactorMin:
            self.zoomFactor = self.zoomFactorMin
            
    def DrawCrosshair(self, event):
        (view_width, view_height) = self.GetClientSize()
        self.buffer = wx.Bitmap(view_width,view_height)
        dc = wx.BufferedDC(wx.ClientDC(self), self.buffer)

        # Draw translated bitmap if it contains data
        if self.image.IsOk():
            oldWidth = self.display_width
            oldHeight = self.display_height
            (self.display_width, self.display_height) = self.GetImageDisplaySize()
    
            if self.newImageData or oldWidth != self.display_width or oldHeight != self.display_height:
                self.displayedImage = self.image.Scale(self.display_width, self.display_height, 
                    quality = self.resizeMethod)
                self.bmp = wx.BitmapFromImage(self.displayedImage)
                self.newImageData = False
            dc.DrawBitmap(self.bmp, self.translation[0], self.translation[1], True)
            subRect = wx.Rect(-self.translation[0], -self.translation[1],
                view_width, view_height)
            print(subRect.Get())
            self.croppedDisplayedImage = \
                self.displayedImage.GetSubImage(subRect)
            
            
            
        position = event.GetPosition()            
        #dc.CrossHair(*position)        
        dc.DrawLine(0, position[1], view_width, position[1])
        dc.DrawLine(position[0], 0, position[0], view_height)
        

                                
            
            
            


    def InitBuffer(self):
        # Setup Display Context equal to size of area to be painted
        (view_width, view_height) = self.GetClientSize()
        self.buffer = wx.Bitmap(view_width,view_height)
        dc = wx.BufferedDC(None, self.buffer)
        
        # Draw translated bitmap if it contains data
        if self.image.IsOk():
            oldWidth = self.display_width
            oldHeight = self.display_height
            (self.display_width, self.display_height) = self.GetImageDisplaySize()
    
            if self.newImageData or oldWidth != self.display_width or oldHeight != self.display_height:
                self.displayedImage = self.image.Scale(self.display_width, self.display_height, 
                    quality = self.resizeMethod)
                self.bmp = wx.BitmapFromImage(self.displayedImage)
                self.newImageData = False
            dc.DrawBitmap(self.bmp, self.translation[0], self.translation[1], True)
            subRect = wx.Rect(-self.translation[0], -self.translation[1],
                view_width, view_height)
            self.croppedDisplayedImage = \
                self.displayedImage.GetSubImage(subRect)


        self.reInitBuffer = False
        

    def OnIdle(self, event):
        if self.reInitBuffer:
            self.InitBuffer()
            self.Refresh()
        event.Skip()
        

    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self, self.buffer)
                  

    def OnSize(self, event):
        self.reInitBuffer = True
        if self.dynamicResize:
            if self.reInitBuffer:
                  self.InitBuffer()
                  self.Refresh()      
        event.Skip()  
  

    def GetImageDisplaySize(self):
        # Should really clean this up!
        if not self.image.IsOk():
            return (1,1)
    
        if self.viewMode == 0:
            (display_width, display_height) = self.image.GetSize()
            self.zoomFactor = 1.0
        elif self.viewMode == 1:
            self.translation = (0,0)
            (view_width, view_height) = self.GetClientSize()
            if self.maintainAspectRatio:
                (img_width, img_height) = self.image.GetSize()
                display_width  = min(view_width,
                    math.floor(1.0*img_width*view_height/img_height))
                display_height = min(view_height,
                    math.floor(1.0*img_height*view_width/img_width))
                self.zoomFactor = 1.0*display_width/img_width
            else:
                (display_width, display_height) = (view_width, view_height)
        elif self.viewMode == 2 or self.viewMode == 3:
            (img_width, img_height) = self.image.GetSize()
            display_width = round(1.0*self.zoomFactor*img_width)
            display_height = round(1.0*self.zoomFactor*img_height)
                
        return (display_width, display_height) 












class ImageControlPanel(wx.Panel):
    """
    This is a control panel for the ImageViewerPanel.
    """
    
    def __init__(self, parent, imageViewerPanel, id = -1):
        wx.Panel.__init__(self, parent, id)
        
        # Set the Image Viewer Panel that this Image Control Panel controls
        self.imageViewerPanel = imageViewerPanel

        # Construct controls
        self.checkBox = wx.CheckBox(self, -1, "Maintain Aspect Ratio", (0, 0), (200, 20))
        self.checkBox.SetValue(self.imageViewerPanel.maintainAspectRatio)

        self.checkBox2 = wx.CheckBox(self, -1, "Dynamic Resize", (0, 20), (200, 20))
        self.checkBox2.SetValue(self.imageViewerPanel.dynamicResize)

        self.checkBox3 = wx.CheckBox(self, -1, "Show Image", (200, 0), (200, 20))
        self.checkBox3.SetValue(False)
        
        self.choice = wx.Choice(self, -1, (0, 40), choices=self.imageViewerPanel.viewModes)
        self.choice.SetSelection(self.imageViewerPanel.viewMode)
        

class ControlledImageViewerPanel(wx.Panel):
    """
    This is an ImageViewerPanel with additional controls for 
    image panning, zooming, etc. 
    """
    
    def __init__(self, parent, id = -1):
        wx.Panel.__init__(self, parent, id)
        self.imageViewerPanel = ImageViewerPanel(self)
        self.imageControlPanel = ImageControlPanel(self, self.imageViewerPanel)
        
        # Create vertical boxsizer
        boxSizer = wx.BoxSizer(wx.VERTICAL)
        boxSizer.Add(self.imageControlPanel, 0, wx.EXPAND)
        boxSizer.Add(self.imageViewerPanel, 1, wx.EXPAND)
        self.SetSizer(boxSizer)


class ImageViewerFrame(wx.Frame):
    """
    This is a basic frame containing functionality to use the
    ControlledImageViewerPanel class.
    """
    # Class data
    imageWildcard = "All Files (*.*)|*.*|" \
                    "PNG (*.png)|*.png|" \
                    "JPEG (*.jpg, *.jpeg)|*.jpg;*.jpeg|" \
                    "TIFF (*.tif, *.tiff)|*.tif;*.tiff|" \
                    "BMP (*.bmp)|*.bmp|"    

    def __init__(self):
        self.title = "Image Viewer"
        wx.Frame.__init__(self, None, -1, self.title, size = (800, 600))
        
        # High-level application data
        self.filename = ""
        self.currentDirectory = ""

        # Attributes 
        statusBar = self.createStatusBar()
        menuBar = self.createMenuBar()
        self.controlledImageViewerPanel = ControlledImageViewerPanel(self)

        # Add drop target
        dropTarget = MyFileDropTarget(self)
        self.SetDropTarget(dropTarget)
        
    def OnOpen(self, event):
        dlg = wx.FileDialog(self, "Open image...",
                os.getcwd(), style=wx.FD_OPEN,
                wildcard = self.imageWildcard)
        if self.currentDirectory:
            dlg.SetDirectory(self.currentDirectory)                
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetPath()
            self.OpenImage()
        dlg.Destroy()
        
    def OpenImage(self):        
        # This code imports the image
        if self.filename:
            try:
                self.SetTitle(self.title + ' - ' +
                    os.path.split(self.filename)[1])
                self.currentDirectory = os.path.split(self.filename)[0]
                fileExtension = os.path.splitext(self.filename)[1].lower()
                if fileExtension == ".png":
                    self.controlledImageViewerPanel.imageViewerPanel.image = wx.Image(self.filename, wx.BITMAP_TYPE_PNG)
                elif fileExtension == ".jpg" or fileExtension == ".jpeg":
                    self.controlledImageViewerPanel.imageViewerPanel.image = wx.Image(self.filename, wx.BITMAP_TYPE_JPEG)
                elif fileExtension == ".tif" or fileExtension == ".tiff":
                    self.controlledImageViewerPanel.imageViewerPanel.image = wx.Image(self.filename, wx.BITMAP_TYPE_TIF)
                elif fileExtension == ".bmp":
                    self.controlledImageViewerPanel.imageViewerPanel.image = wx.Image(self.filename, wx.BITMAP_TYPE_BMP)
                else:
                    # nolog = wx.LogNull() # Uncommenting will not log errors
                    self.imageViewerPanel.image = wx.Image(self.filename, wx.BITMAP_TYPE_ANY)
                    #del nolog
                self.controlledImageViewerPanel.imageViewerPanel.newImageData = True
            except:
                wx.MessageBox("Error importing %s." % self.filename, "oops!",
                    stype=wx.IsOk|wx.ICON_EXCLAMATION)          
        
    def OnCloseWindow(self, event):
        pass
        
    def OnCopy(self, event):
        pass
        
    def OnPaste(self, event):
        pass
        
    def createStatusBar(self):
        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(3)
        self.statusbar.SetStatusWidths([200, -2, -3])        

    def menuData(self):
        return (("&File",
                    ("&Open...\tCtrl-O",    "Open image",   self.OnOpen),
                    ("&Quit\tCtrl-Q",       "Quit",         self.OnCloseWindow)),
                ("&Edit",
                    ("&Copy\tCtrl-C",       "Copy image",   self.OnCopy),
                    ("&Paste\tCtrl-V",      "Paste image",  self.OnPaste))
                )
        
    def createMenuBar(self):
        menuBar = wx.MenuBar()
        for eachMenuData in self.menuData():
            menuLabel = eachMenuData[0]
            menuItems = eachMenuData[1:]
            menu = self.createMenu(menuItems)
            menuBar.Append(menu, menuLabel)        
        self.SetMenuBar(menuBar)
        return menuBar
        
    def createMenu(self, menuItems):
        menu = wx.Menu()
        for eachLabel, eachStatus, eachHandler in menuItems:
            if not eachLabel:
                menu.AppendSeparator()
                continue
            menuItem = menu.Append(-1, eachLabel, eachStatus)
            self.Bind(wx.EVT_MENU, eachHandler, menuItem)
        return menu   
        
class MyFileDropTarget(wx.FileDropTarget):

    def __init__(self, window):
        wx.FileDropTarget.__init__(self)
        self.window = window
    
    def OnDropFiles(self, x, y, filenames):
        if len(filenames) > 1:
            dlg = wx.MessageBox( 
                "This application only supports opening a single image.",
                "Multiple images detected", wx.IsOk | wx.ICON_EXCLAMATION)
            return
#         if os.path.splitext(filenames[0])[1].lower() == ".jpg":
#             self.window.filename = filenames[0]
#             self.window.ImportImage()
        

if __name__ == "__main__":
    app = wx.App()
    frame = ImageViewerFrame()
    frame.Show()
    app.MainLoop()
    
    
    
    
    
    
    
    
    
    
    
    
    
            
        
        
        
     