# HR June 2019 onwards
# Version 5 to follow HHC's StrEmbed-4 in Perl
# User interface for lattice-based assembly configurations

### ---
# HR 17/10/19
# Version 5.1 to draw main window as panels within flexgridsizer
# Avoids confusing setup for staticbox + staticboxsizer
### ---

### ---
# HR 12/12/2019 onwards
# Version 5.2
### ---

### BUGS LOG
# 1 // 7/2/20
# Images in geometry view does not update when resized until next resize
# e.g. when maximised, images remain small
# FIXED Feb 2020 with CallAfter
# ---
# 2 // 7/2/20
# Image rescaling (via ScaleImage method) may need correction
# Sometimes appears that images overlap border of toggle buttons partly
# ---
# 3 // 6/3/20
# Assembly operation methods (flatten, assemble, etc.) need compressing into fewer methods
# as currently a lot of repeated code



# WX stuff
import wx
# WX customtreectrl for parts list
import wx.lib.agw.customtreectrl as ctc
# Allows inspection of app elements via Ctrl + Alt + I
# Use InspectableApp() in MainLoop()
import wx.lib.mixins.inspection as wit
# For scrolled panel
import wx.lib.scrolledpanel as scr

# matplotlib stuff
import matplotlib as mpl
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar

# Ordered dictionary
from collections import OrderedDict as odict

# OS operations for exception-free file checking
import os.path

# Import networkx for plotting lattice
import networkx as nx

# Gets rid of blurring throughout application by getting DPI info
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(True)
except:
    pass

# For STEP import
from step_parse_5_2 import StepParse



class MyCustomTreeCtrl(ctc.CustomTreeCtrl):
    
    def __init__(self, parent, style):
        ctc.CustomTreeCtrl.__init__(self, parent, agwStyle = style)
        self.parent = parent
        self.reverse_sort = False
        self.alphabetical = True
        

        
    # Overridden method to allow sorting based on data other than text
    # Can be sorted alphabetically or numerically, and in reverse
    # ---
    # This method is called by sorting methods
    # ---
    # NOTE the functionality necessary for this was added to the wxWidgets / Phoenix Github repo
    # in 2018 in response to issue #774 here: https://github.com/wxWidgets/Phoenix/issues/774
    def OnCompareItems(self, item1, item2):

        if self.alphabetical:
            t1 = self.GetItemText(item1)
            t2 = self.GetItemText(item2)
        else:
            t1 = self.GetPyData(item1)['sort_id']
            t2 = self.GetPyData(item2)['sort_id']
        
        if self.reverse_sort:
            reverse = -1
        else:
            reverse = 1
            
        if t1 < t2: return -1*reverse
        if t1 == t2: return 0
        return 1*reverse
    
    
    
    def GetAncestors(self, item):
        
        # Get all children recursively
        # ---
        # MUST create shallow copy of children here to avoid strange behaviour
        # According to ctc docs, "It is advised not to change this list
        # [i.e. returned list] and to make a copy before calling
        # other tree methods as they could change the contents of the list."
        ancestors = item.GetChildren().copy()
        # They mess you up, your mum and dad
        parents = ancestors
        while parents:
            # They may not mean to, but they do
            children = []
            for parent in parents:
                children = parent.GetChildren().copy()
                # They fill you with the faults they had
                ancestors.extend(children)
                # And add some extra, just for you
                parents = children
        return ancestors


    
    def SortAllChildren(self, item):

        # Get all non-leaf nodes of parent object (always should be MainWindow)
        nodes = self.GetAncestors(item)
        nodes = [el for el in nodes if el.HasChildren()]
        for node in nodes:
            count = self.GetChildrenCount(node, recursively = False)
            if count > 1:
                self.SortChildren(node)



class MainWindow(wx.Frame):

    # Constructor
    def __init__(self):
        
        ### CREATE OBJECT FOR ASSEMBLY MANAGEMENT
        self.a = []

        
        
        wx.Frame.__init__(self, parent = None, title = "StrEmbed-5-2")
        self.SetBackgroundColour('white')
                
        
        
        ### MENU BAR
        menuBar  = wx.MenuBar()

        fileMenu = wx.Menu()
        menuBar.Append(fileMenu, "&File")
        fileOpen = fileMenu.Append(wx.ID_OPEN, "&Open", "Open file")
        fileSave = fileMenu.Append(wx.ID_SAVE, "&Save", "Save file")
        fileSaveAs = fileMenu.Append(wx.ID_SAVEAS, "&Save as", "Save file as")
        fileClose = fileMenu.Append(wx.ID_CLOSE, "&Close", "Close file")
        fileExit = fileMenu.Append(wx.ID_EXIT, "&Exit", "Exit program")

        partMenu = wx.Menu()
        menuBar.Append(partMenu, "&Parts")

        geomMenu = wx.Menu()
        menuBar.Append(geomMenu, "&Geometry")

        lattMenu = wx.Menu()
        menuBar.Append(lattMenu, "&Lattice")

        abtMenu   = wx.Menu()
        menuBar.Append(abtMenu,  "&About")
        menuAbout = abtMenu.Append(wx.ID_ABOUT,"&About", "About PyStrEmbed-1")

        self.SetMenuBar(menuBar)



        # Bindings for menu items
        self.Bind(wx.EVT_MENU, self.OnFileOpen,      fileOpen)
        self.Bind(wx.EVT_MENU, self.DoNothingDialog, fileSave)
        self.Bind(wx.EVT_MENU, self.DoNothingDialog, fileSaveAs)
        self.Bind(wx.EVT_MENU, self.OnExit,  fileClose)
        self.Bind(wx.EVT_MENU, self.OnExit,  fileExit)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)



        ### TOOLBAR
        # Main window toolbar with assembly operations
        self.tb = wx.ToolBar(self, style = wx.TB_NODIVIDER | wx.TB_FLAT)
        self.SetToolBar(self.tb)
        self.tb.SetToolBitmapSize((40,40))
        self.tb.SetBackgroundColour('white')
        
        # File tools
        self.fileOpenTool  = self.tb.AddTool(wx.ID_ANY, 'Open',  wx.Bitmap("Images/fileopen.bmp"),  bmpDisabled = wx.NullBitmap,
                                   shortHelp = 'File open',  longHelp = 'File open')
        self.exitTool      = self.tb.AddTool(wx.ID_ANY, 'Exit', wx.Bitmap("Images/fileclose.bmp"), bmpDisabled = wx.NullBitmap,
                                   shortHelp = 'Exit', longHelp = 'Exit')
        self.tb.AddSeparator()
        
        # Assembly tools
        self.assembleTool = self.tb.AddTool(wx.ID_ANY, 'Assemble', wx.Bitmap("Images/assemble.bmp"), bmpDisabled = wx.NullBitmap,
                                 shortHelp = 'Assemble',   longHelp = 'Form assembly from selected parts')
        self.flattenTool = self.tb.AddTool(wx.ID_ANY, 'Flatten', wx.Bitmap("Images/flatten.bmp"), bmpDisabled = wx.NullBitmap,
                                 shortHelp = 'Flatten', longHelp = 'Flatten selected assembly')
        self.disaggregateTool = self.tb.AddTool(wx.ID_ANY, 'Disaggregate', wx.Bitmap("Images/disaggregate.bmp"), bmpDisabled = wx.NullBitmap,
                                 shortHelp = 'Disaggregate', longHelp = 'Disaggregate selected assembly')
        self.aggregateTool = self.tb.AddTool(wx.ID_ANY, 'Aggregate', wx.Bitmap("Images/aggregate.bmp"), bmpDisabled = wx.NullBitmap,
                                 shortHelp = 'Aggregate', longHelp = 'Aggregate selected assembly')
        self.addNodeTool = self.tb.AddTool(wx.ID_ANY, 'Add node', wx.Bitmap("Images/add_node.bmp"), bmpDisabled = wx.NullBitmap,
                                 shortHelp = 'Add node', longHelp = 'Add node to selected assembly')
        self.removeNodeTool = self.tb.AddTool(wx.ID_ANY, 'Remove node', wx.Bitmap("Images/remove_node.bmp"), bmpDisabled = wx.NullBitmap,
                                 shortHelp = 'Remove node', longHelp = 'Remove selected node')
        self.sortTool = self.tb.AddTool(wx.ID_ANY, 'Toggle sort type', wx.Bitmap("Images/sort_mode.bmp"), bmpDisabled = wx.NullBitmap,
                                 shortHelp = 'Toggle sort type', longHelp = 'Toggle sort type (alphabetical/by unique item ID)')
        self.sortReverseTool = self.tb.AddTool(wx.ID_ANY, 'Reverse sort order', wx.Bitmap("Images/sort_reverse.bmp"), bmpDisabled = wx.NullBitmap,
                                 shortHelp = 'Reverse sort order', longHelp = 'Reverse sort order: sort all if no items selected')
        self.tb.Realize()



        # Bind toolbar tools to actions
        self.Bind(wx.EVT_TOOL, self.OnFileOpen, self.fileOpenTool)
        self.Bind(wx.EVT_TOOL, self.OnExit,     self.exitTool)
        
        self.Bind(wx.EVT_TOOL, self.OnAssemble, self.assembleTool)
        self.Bind(wx.EVT_TOOL, self.OnFlatten, self.flattenTool)
        self.Bind(wx.EVT_TOOL, self.OnDisaggregate, self.disaggregateTool)
        self.Bind(wx.EVT_TOOL, self.OnAggregate, self.aggregateTool)
        self.Bind(wx.EVT_TOOL, self.OnAddNode, self.addNodeTool)
        self.Bind(wx.EVT_TOOL, self.OnRemoveNode, self.removeNodeTool)
        
        self.Bind(wx.EVT_TOOL, self.OnSortTool, self.sortTool)
        self.Bind(wx.EVT_TOOL, self.OnSortReverseTool, self.sortReverseTool)
       


        ### STATUS BAR
        # Status bar
        self.statbar = self.CreateStatusBar()
        self.statbar.SetBackgroundColour('white')
        # Update status bar with window size on (a) first showing and (b) resizing
        self.Bind(wx.EVT_SIZE, self.OnResize)



        # Create main panel
        self.InitMainPanel()



    def InitMainPanel(self):

        ### MAIN PANEL
        #
        # Create main panel to contain everything
        self.panel = wx.Panel(self)
        self.box   = wx.BoxSizer(wx.VERTICAL)

        # Create FlexGridSizer to have 3 panes
        # 2nd and 3rd arguments are hgap and vgap b/t panes (cosmetic)
        self.grid = wx.FlexGridSizer(cols = 3, rows = 2, hgap = 10, vgap = 10)

        self.part_header = wx.StaticText(self.panel, label = "Parts view")
        self.geom_header = wx.StaticText(self.panel, label = "Geometry view")
        self.latt_header = wx.StaticText(self.panel, label = "Lattice view")

        self.panel_style = wx.SIMPLE_BORDER
        self.part_panel = wx.Panel(self.panel, style = self.panel_style)
        self.geom_panel = scr.ScrolledPanel(self.panel, style = self.panel_style)
        self.geom_panel.SetupScrolling()
        self.latt_panel = wx.Panel(self.panel, style = self.panel_style)

        self.part_sizer = wx.BoxSizer(wx.VERTICAL)
        self.latt_sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Some special setup for geometry sizer (grid)
        self.image_cols = 2
        self.geom_sizer = wx.FlexGridSizer(cols = self.image_cols, rows = 0, hgap = 5, vgap = 5)
        # Defines tightness of images in grid
        self.geom_tight = 0.95


        # PARTS VIEW SETUP
        # Custom tree ctrl implementation
        self.treeStyle = (ctc.TR_MULTIPLE | ctc.TR_EDIT_LABELS | ctc.TR_HAS_BUTTONS)
#        self.partTree_ctc = ctc.CustomTreeCtrl(self.part_panel, agwStyle = self.treeStyle)
        self.partTree_ctc = MyCustomTreeCtrl(self.part_panel, style = self.treeStyle)
        self.partTree_ctc.SetBackgroundColour('white')
        self.part_sizer.Add(self.partTree_ctc, 1, wx.EXPAND)
        
        
        self.partTree_ctc.Bind(wx.EVT_RIGHT_DOWN,          self.OnPartsRC)
        self.partTree_ctc.Bind(wx.EVT_TREE_BEGIN_DRAG,     self.OnTreeDrag)
        self.partTree_ctc.Bind(wx.EVT_TREE_END_DRAG,       self.OnTreeDrop)
        self.partTree_ctc.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnTreeLabelEditEnd)



        # GEOMETRY VIEW SETUP
        # Set up image-view grid, where "rows = 0" means the sizer updates dynamically
        # according to the number of elements it holds
#        self.geom_sizer.Add(self.image_grid, 1, wx.EXPAND)

        # Binding for toggling of part/assembly images
        # though toggle buttons realised later
        self.Bind(wx.EVT_TOGGLEBUTTON, self.ImageToggled)
        
        self.no_image_ass  = 'Images/noimage_ass.png'
        self.no_image_part = 'Images/noimage_part.png'



        # LATTICE VIEW SETUP
        # Set up matplotlib FigureCanvas with toolbar for zooming and movement
        self.latt_figure = mpl.figure.Figure()
        self.latt_canvas = FigureCanvas(self.latt_panel, -1, self.latt_figure)
        self.latt_axes   = self.latt_figure.add_subplot(111)
        self.latt_canvas.Hide()

        # Realise but hide, to be shown later when file loaded/data updated
        self.latt_tb = NavigationToolbar(self.latt_canvas)
#        self.latt_tb.Realize()
        self.latt_tb.Hide()

        self.latt_sizer.Add(self.latt_canvas, 1, wx.EXPAND | wx.ALIGN_BOTTOM | wx.ALL, border = 5)
        self.latt_sizer.Add(self.latt_tb, 0, wx.EXPAND)

        self.selected_colour = 'blue'
        
        self.latt_panel.Bind(wx.EVT_MOTION, self.MouseMoved)

        self.latt_canvas.mpl_connect('button_press_event',   self.GetLattPos)
        self.latt_canvas.mpl_connect('button_release_event', self.LattNodeSelected)
        
        self.new_assembly_text = 'Unnamed item'
        self.new_part_text     = 'Unnamed item'
        


        # OVERALL SIZERS SETUP
        self.part_panel.SetSizer(self.part_sizer)
        self.geom_panel.SetSizer(self.geom_sizer)
        self.latt_panel.SetSizer(self.latt_sizer)

        self.grid.AddMany([(self.part_header), (self.geom_header), (self.latt_header),
                           (self.part_panel, 1, wx.EXPAND), (self.geom_panel, 1, wx.EXPAND), (self.latt_panel, 1, wx.EXPAND)])

        # Set all grid elements to "growable" upon resizing
        # Flags (second argument is proportional size)
        self.grid.AddGrowableRow(1,0)
        self.grid.AddGrowableCol(0,3)
        self.grid.AddGrowableCol(1,2)
        self.grid.AddGrowableCol(2,3)

        # Set sizer for/update main panel
        self.box.Add(self.grid, 1, wx.ALL | wx.EXPAND, 5)
        self.panel.SetSizer(self.box)

        # Set max panel sizes to avoid resizing issues
        self.part_panel_max = self.part_panel.GetSize()
        self.part_panel.SetMaxSize(self.part_panel_max)
        self.geom_panel_max = self.geom_panel.GetSize()
        self.geom_panel.SetMaxSize(self.geom_panel_max)
        self.latt_panel_max = self.latt_panel.GetSize()
        self.latt_panel.SetMaxSize(self.latt_panel_max)

        # "File is open" tag
        self.file_open = False
        
        

    def GetFilename(self, dialog_text = "Open file", starter = None, ender = None):

        ### General file-open method; takes list of file extensions as argument
        ### and can be used for specific file names ("starter", string)
        ### or types ("ender", string or list)

        # Convert "ender" to list if only one element
        if isinstance(ender, str):
            ender = [ender]

        # Check that only one kwarg is present
        # Create text for file dialog
        if starter is not None and ender is None:
            file_open_text = starter.upper() + " files (" + starter.lower() + "*)|" + starter.lower() + "*"
        elif starter is None and ender is not None:
            file_open_text = [el.upper() + " files (*." + el.lower() + ")|*." + el.lower() for el in ender]
            file_open_text = "|".join(file_open_text)
        else:
            raise ValueError("Requires starter or ender only")

        # Create file dialog
        fileDialog = wx.FileDialog(self, dialog_text, "", "",
                                   file_open_text,
                                   wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        fileDialog.ShowModal()
        filename = fileDialog.GetPath()
        fileDialog.Destroy()

        # Return file name, ignoring rest of path
        return filename



    def DisplayPartsList(self):
        
        # Check if file loaded previously
        try:
            self.partTree_ctc.DeleteAllItems()
        except:
            pass

        # Create root node...
        root_id  = self.assembly.tree.root
        root_tag = self.assembly.tree.get_node(root_id).tag
        
        ctc_root_item = self.partTree_ctc.AddRoot(text = root_tag, ct_type = 1, data = {'id_': root_id, 'sort_id': root_id})
        self.ctc_dict[root_id] = ctc_root_item
        self.ctc_dict_inv[ctc_root_item] = root_id

#        # ...then all others
#        # Assumes treelib ordering ensures parents are defined before children
#        for el in self.assembly.tree_dict:
#            if el != root_id:
#                parent_id = self.assembly.tree.parent(el).identifier
#                ctc_parent = self.ctc_dict[parent_id]
#                ctc_text = self.assembly.part_dict[self.assembly.tree_dict[el]]
#                ctc_item = self.partTree_ctc.AppendItem(ctc_parent, text = ctc_text, ct_type = 1)
#                self.ctc_dict[el]           = ctc_item
#                self.ctc_dict_inv[ctc_item] = el

        # HR 14/02/20: LOOP THROUGH NODES AT EACH DEPTH
        # DOES NOT assume treelib ordering ensures parents are defined before children
        # ...then all others
        tree_depth = self.assembly.tree.depth()
        for i in range(tree_depth + 1)[1:]:
            for el in self.assembly.tree.nodes:
                if self.assembly.tree.depth(el) == i:
                    parent_id = self.assembly.tree.parent(el).identifier
                    ctc_parent = self.ctc_dict[parent_id]
                    try:
#                        ctc_text = self.assembly.part_dict[self.assembly.tree_dict[el]]
                        ctc_text = self.assembly.tree.nodes[el].tag
                    except:
                        ctc_text = self.new_assembly_text
                    ctc_item = self.partTree_ctc.AppendItem(ctc_parent, text = ctc_text, ct_type = 1, data = {'id_': el, 'sort_id': el})
                    self.ctc_dict[el]           = ctc_item
                    self.ctc_dict_inv[ctc_item] = el

        
        # Binding for checking of list items
        self.Bind(ctc.EVT_TREE_ITEM_CHECKED, self.TreeItemChecked)
        self.Bind(ctc.EVT_TREE_SEL_CHANGED,  self.TreeItemSelected)
        
        self.partTree_ctc.ExpandAll()

        # Sort all tree items
        self.partTree_ctc.SortAllChildren(self.partTree_ctc.GetRootItem())
        
        
        
    def ScaleImage(self, img, p_w = None, scaling = 0.90):
        
        # Get size of panel holding image if not given as argument
        if p_w == None:
            p_w  = self.geom_panel.GetSize()[0]/self.image_cols
        
        h, w = img.GetSize()
        
        if h/w > 1:
            h_new = p_w
            w_new = h_new*w/h
        else:
            w_new = p_w
            h_new = w_new*h/w
        
        #Rescale
        img = img.Scale(w_new*scaling, h_new*scaling)

        return img



    def TreeItemChecked(self, event):
        
        # Get checked item and search for corresponding image
        #
        item = event.GetItem()
        id_  = self.ctc_dict_inv[item]
        
        self.selected_items = self.partTree_ctc.GetSelections()

        if item.IsChecked():
            # Get image
            # ---
            # Try to find pre-rendered image in folder
            img = self.assembly.tree_dict[id_]
            img = os.path.join('Images', img + '.png')
            if os.path.isfile(img):
                img = wx.Image(img, wx.BITMAP_TYPE_ANY)
            else:
                if id_ in self.assembly.leaf_ids:
                    img = wx.Image(self.no_image_part, wx.BITMAP_TYPE_ANY)
                else:
                    img = wx.Image(self.no_image_ass, wx.BITMAP_TYPE_ANY)
            
            # Create/add button in geom_panel
            # 
            # Includes rescaling to panel
            img_sc = self.ScaleImage(img)
            # 1/ TEST: Start with null image... 
            button = wx.BitmapToggleButton(self.geom_panel)
            button.SetBackgroundColour('white')
            self.geom_sizer.Add(button, 1, wx.EXPAND)
            # 2/ Add image after computing size
            button.SetBitmap(wx.Bitmap(self.ScaleImage(img_sc)))
            
            # Update global list and dict
            #
            # Data is list, i.e. same format as "selected_items"
            # but ctc lacks "get selections" method for checked items
            self.checked_items.append(item)
            self.button_dict[id_]         = button
            self.button_dict_inv[button]  = id_
            self.button_img_dict[id_]     = img
            
            # Toggle if already selected elsewhere
            if self.ctc_dict[id_] in self.selected_items:
                button.SetValue(True)
            else:
                pass
            
        else:
            # Remove button from geom_panel
            obj = self.button_dict[id_]
            obj.Destroy()
            
            # Update global list and dict
            self.checked_items.remove(item)
            self.button_dict.pop(id_)
            self.button_dict_inv.pop(obj)
            self.button_img_dict.pop(id_)
           
        self.geom_panel.SetupScrolling(scrollToTop = False)



    def TreeItemSelected(self, event):
        
        # Get selected item and update global list of items
        #
        # Using GetSelection rather than maintaining list of items
        # as with checked items b/c releasing ctrl key during multiple
        # selection means not all selections are tracked easily
        self.selected_items = self.partTree_ctc.GetSelections()
        
        self.UpdateToggledImages()
        self.UpdateLatticeSelections()



    def ImageToggled(self, event):
        
        id_ = self.button_dict_inv[event.GetEventObject()]
        self.UpdateListSelections(id_)
        
        self.UpdateLatticeSelections()



    def GetLattPos(self, event):
        
        print('%s: button = %d, x = %d, y = %d, xdata = %f, ydata = %f' %
              ('Double click' if event.dblclick else 'Single click', event.button,
               event.x, event.y, event.xdata, event.ydata))

        # Get position of click event
        self.click_pos = (event.x, event.y)
        
        
        
    def LattNodeSelected(self, event):
        
        # Functor to find nearest value in sorted list
        # ---
        # HR 4/3/20 THIS SHOULD BE REWRITTEN COMPLETELY TO USE MPL PICKER/ARTIST FUNCTIONALITY
        def get_nearest(value, list_in):
                            
            # First check if value beyond upper bound
            if value > list_in[-1]:
                print('case 1: beyond upper bound')
                answer = list_in[-1]
                
            else:
                for i,el in enumerate(list_in):
                    if value < el:
                        
                        # Then check if below lower bound
                        if i == 0:
                            print('case 2: below lower bound')
                            answer = list_in[0]
                            break

                        # All other cases: somewhere in between
                        else:
                            print('case 3: intermediate')
                            if abs(value - el) < abs(value - list_in[i-1]):
                                answer = el
                            else:
                                answer = list_in[i-1]
                            break
                    
            return answer
                       
        if event.x == self.click_pos[0] and event.y == self.click_pos[1]:
            
            # Get nearest y value (same as lattice level)#
            # Must prepend lattice level of single part to list
            y_list = self.assembly.levels_a_sorted[:]
            y_list.insert(0, self.assembly.part_level)
            y_  = get_nearest(event.ydata, y_list)
            
            # Get nearest x value within known y level
            x_dict = {self.assembly.g.nodes[el]['pos'][0]:el for el in self.assembly.levels_a_inv[y_]}
            x_list = [k for k,v in x_dict.items()]
            x_  = get_nearest(event.xdata, sorted(x_list))
            
            # Get nearest node
            id_ = x_dict[x_]
            
            print('Nearest node: x = %f, y = %f; node ID: %i\n' %
                  (x_, y_, id_))
            
            self.latt_plotlims = (self.latt_axes.get_xlim(), self.latt_axes.get_ylim())
            print(self.latt_plotlims)
            
            self.UpdateListSelections(id_)

        

    def UpdateListSelections(self, id_):
        
        # Select/deselect parts list item
        item = self.ctc_dict[id_]
        if item in self.selected_items:
            self.selected_items.remove(item)
        else:
            self.selected_items.append(item)
        
        # With "select = True", SelectItem toggles state if multiple selections enabled
        self.partTree_ctc.SelectItem(self.ctc_dict[id_], select = True)



    def UpdateLatticeSelections(self):
        
        # Update colour of selected items
        #
        # Set all back to default colour first
        for node in self.assembly.g.nodes():
            self.assembly.g.nodes[node]['colour'] = self.assembly.default_colour
        # Then selected nodes
        for item in self.selected_items:
            id_ = self.ctc_dict_inv[item]
            self.assembly.g.nodes[id_]['colour'] = self.selected_colour
        
        # Redraw lattice
        self.DisplayLattice()


    
    def UpdateToggledImages(self):
        
        for id_, button in self.button_dict.items():
            button.SetValue(False)
        
        for item in self.selected_items:
            id_    = self.ctc_dict_inv[item]
            if id_ in self.button_dict:
                button = self.button_dict[id_]
                button.SetValue(True)
            else:
                pass
        


    def DisplayLattice(self):

        # Get node positions, colour map, labels
        pos         = nx.get_node_attributes(self.assembly.g, 'pos')
        colour_map  = [self.assembly.g.nodes[el]['colour'] for el in self.assembly.g.nodes]
#        node_labels = nx.get_node_attributes(self.assembly.g, 'label')
        
        try:
            self.latt_axes.clear()
        except:
            pass
        
        # Draw to lattice panel figure
        nx.draw(self.assembly.g, pos, node_color = colour_map, with_labels = True, ax = self.latt_axes)
#        nx.draw_networkx_labels(self.assembly.g, pos, labels = node_labels, ax = self.latt_axes)

        # Minimise white space around plot in panel
        self.latt_figure.subplots_adjust(left = 0.01, bottom = 0.01, right = 0.99, top = 0.99)
        
        try:
            self.latt_axes.set_xlim(self.latt_plotlims[0])
            self.latt_axes.set_ylim(self.latt_plotlims[1])
        except:
            pass

        # Show lattice figure
        self.latt_canvas.draw()
        self.latt_canvas.Show()
        self.latt_tb.Show()

        # Update lattice panel layout
        self.latt_panel.Layout()



    def OnFileOpen(self, event):
        
        # Get STEP filename
        self.open_filename = self.GetFilename(ender = ["stp", "step"]).split("\\")[-1]
        
        # Return if filename is empty, i.e. if user selects "cancel" in file-open dialog
        if not self.open_filename:
            return

        # "File is open" tag
        self.file_open = True
        
        # Tracker for assembly modifications
        self.changes_made_to_assembly = False

        # Append to assembly manager
        self.a.append(StepParse())



        # Load data, create nodes and edges, etc.
        self.assembly = self.a[-1]
        self.assembly.load_step(self.open_filename)
        self.assembly.create_tree()
        
        # Write interactive parts list using WX customtreectrl, from treelib nodes
        self.ctc_dict     = {}
        self.ctc_dict_inv = {}

        # Checked and selected items lists, shared b/t all views
        self.checked_items  = []
        self.selected_items = []

        # Toggle buttons
        self.button_dict     = odict()
        self.button_dict_inv = odict()
        self.button_img_dict = {}



        # Show parts list and lattice
        self.DisplayPartsList()
        
        # Clear geometry window if necessary
        try:
            self.geom_sizer.Clear(True)
        except:
            pass    
        
        # Clear lattice plot if necessary
        try:
            self.latt_axes.clear()
        except:
            pass
        
        # Display lattice
        self.DisplayLattice()



    def OnPartsRC(self, event = None):
        
        # HR 5/3/20 SOME DUPLICATION HERE WITH OPERATION-SPECIFIC METHOD, E.G. "ONFLATTEN"
        # IN TERMS OF FILTERING/SELECTION OF OPTIONS BASED ON SELECTED ITEM TYPE/QUANTITY
        
        # HR 5/3/20 SHOULD ADD CHECK HERE THAT MOUSE CLICK IS OVER A SELECTED ITEM
        pos = event.GetPosition()
               
        # Check selected items are present and suitable
        if not self.selected_items_check():
            print('No items selected')
            return

        # POPUP MENU (WITH BINDINGS) UPON RIGHT-CLICK IN PARTS VIEW
        # ---
        menu = wx.Menu()

        # FILTERING OF ITEM TYPES -> PARTICULAR POP-UP MENU OPTIONS
        # ---
        # Single-item options
        if len(self.selected_items) == 1:
            id_ = self.ctc_dict_inv[self.selected_items[-1]]
            # Part options
            if id_ in self.assembly.leaf_ids:
                menu_item = menu.Append(wx.ID_ANY, 'Disaggregate', 'Disaggregate part into parts')
                self.Bind(wx.EVT_MENU, self.OnDisaggregate, menu_item)
                menu_item = menu.Append(wx.ID_ANY, 'Remove part', 'Remove part')
                self.Bind(wx.EVT_MENU, self.OnRemoveNode, menu_item)
            # Assembly options
            else:
                menu_item = menu.Append(wx.ID_ANY, 'Flatten', 'Flatten assembly')
                self.Bind(wx.EVT_MENU, self.OnFlatten, menu_item)
                menu_item = menu.Append(wx.ID_ANY, 'Aggregate', 'Aggregate assembly')
                self.Bind(wx.EVT_MENU, self.OnAggregate, menu_item)
                menu_item = menu.Append(wx.ID_ANY, 'Add node', 'Add node to assembly')
                self.Bind(wx.EVT_MENU, self.OnAddNode, menu_item)
                # Sorting options
                menu_text = 'Sort children alphabetically'
                menu_item = menu.Append(wx.ID_ANY, menu_text, menu_text)
                self.Bind(wx.EVT_MENU, self.OnSortAlpha, menu_item)
                menu_text = 'Sort children by unique ID'
                menu_item = menu.Append(wx.ID_ANY, menu_text, menu_text)
                self.Bind(wx.EVT_MENU, self.OnSortByID, menu_item)

        # Multiple-item options
        elif len(self.selected_items) > 1:
            menu_item = menu.Append(wx.ID_ANY, 'Assemble', 'Form assembly from selected items')
            self.Bind(wx.EVT_MENU, self.OnAssemble, menu_item)
            menu_item = menu.Append(wx.ID_ANY, 'Remove parts', 'Remove parts')
            self.Bind(wx.EVT_MENU, self.OnRemoveNode, menu_item)
            
        self.PopupMenu(menu, pos)
        menu.Destroy()



    def OnAssemble(self, event = None):
        
        # Check selected items are present and suitable
        if not self.selected_items_check():
            print('No items selected')
            return
        
        # Further checks
        self.selected_list = []
        if len(self.selected_items) > 1:
            print('Selected items to assemble:\n')
            for item in self.selected_items:
                id_ = self.ctc_dict_inv[item]
                print('ID = ', id_)
                self.selected_list.append(id_)
        else:
            print('Cannot assemble: no items or only one item selected\n')
            return
        
        # Check root is not present in selected items
        if self.assembly.tree.root in self.selected_list:
            print('Cannot create assembly: items to assemble include root')
            return
         
        # Check with user whether to proceed, as link to STEP file will be lost
        if not self.changes_made_to_assembly:
            caption = 'Create sub-assembly?'
            message = 'Do you want to modify the assembly? Previous assembly will be retained'

            if self.okay_to_proceed(message, caption):
                print('Okay to proceed!')
                self.changes_made_to_assembly = True
            else:
                print('Not proceeding!')
                return
                
        # MAIN "ASSEMBLE" ALGORITHM
        # ---
        # Get selected item that is highest up tree (i.e. lowest depth)
        depths = {}
        for id_ in self.selected_list:
            depths[id_] = self.assembly.tree.depth(id_)
            print('ID = ', id_, '; parent depth = ', depths[id_])
        highest_node = min(depths, key = depths.get)
        parent_      = self.assembly.tree.parent(highest_node).identifier
        
        # Get valid ID for new node then create
        new_id   = self.create_new_id()
        new_node = self.assembly.tree.create_node(tag = self.new_assembly_text, parent = parent_, identifier = new_id)
        print('New assembly ID = ', new_node.identifier)
        self.assembly.tree_dict[new_node.identifier] = self.new_assembly_text
        
        # Move all selected items to be children of new node
        for id_ in self.selected_list:
            self.assembly.tree.move_node(id_, new_node.identifier)
        
        # Propagate changes
        self.ClearGUIItems()
        self.OnTreeCtrlChanged()
        
        
        
    def create_new_id(self):
        
        # Get new item ID that is greater than largest existing ID in tree ctrl
        id_ = max(self.assembly.tree_dict) + 1
        return id_
        
        
    
    def OnTreeCtrlChanged(self):
        
        # Remake parts list and lattice
        # HR 17/02/2020 MUST BE IMPROVED SO ONLY AFFECTED CTC AND LATTICE ITEMS MODIFIED
        self.DisplayPartsList()
        self.assembly.get_levels()
        self.assembly.create_lattice()
        self.DisplayLattice()
        


    def OnFlatten(self, event):
        
        # Check selected items are present and suitable
        if not self.selected_items_check():
            print('No items selected')
            return
        
        # Further checks
        if len(self.selected_items) == 1:
            id_ = self.ctc_dict_inv[self.selected_items[-1]]
            if id_ not in self.assembly.leaf_ids:
                print('ID of item to flatten = ', id_)
            else:
                print('Cannot flatten: item is a leaf node/irreducible part\n')
                return
        else:
            print('Cannot flatten: more than one item selected\n')
            return

        # Check with user whether to proceed, as link to STEP file will be lost
        if not self.changes_made_to_assembly:
            caption = 'Flat sub-assembly?'
            message = 'Do you want to modify the assembly? Previous assembly will be retained'
    
            if self.okay_to_proceed(message, caption):
                print('Okay to proceed!')
                self.changes_made_to_assembly = True
            else:
                print('Not proceeding!')
                return
        
        # MAIN "FLATTEN" ALGORITHM
        # ---
        # Get immediate children of item
        children_      = self.assembly.get_all_children(id_)
        children_parts = [el for el in children_ if el in self.assembly.leaf_ids]
        print('Children parts = ', children_parts)
        children_ass   = [el for el in children_ if not el in self.assembly.leaf_ids]
        print('Children assemblies = ', children_ass)

        
        # Move all children that are indivisible parts
        for child in children_parts:
            self.assembly.tree.move_node(child, id_)
        
        # Delete all children that are assemblies
        # Try/except block as children of assemblies may be removed after parent
        for child in children_ass:
            try:
                self.assembly.tree.remove_node(child)
            except:
                pass
        
        # Propagate changes
        self.ClearGUIItems()
        self.OnTreeCtrlChanged()
        
        
        
    def OnDisaggregate(self, event = None):

        # Check selected items are present and suitable
        if not self.selected_items_check():
            print('No items selected')
            return
        
        # Further checks
        if len(self.selected_items) == 1:
            id_ = self.ctc_dict_inv[self.selected_items[-1]]
            if id_ in self.assembly.leaf_ids:
                print('ID of item to disaggregate = ', id_)
            else:
                print('Cannot disaggregate: item is not a leaf node/irreducible part\n')
                return
        else:
            print('Cannot disaggregate: no or more than one item selected\n')
            return
        
        # Check with user whether to proceed, as link to STEP file will be lost
        if not self.changes_made_to_assembly:
            caption = 'Create sub-assembly?'
            message = 'Do you want to modify the assembly? Previous assembly will be retained'

            if self.okay_to_proceed(message, caption):
                print('Okay to proceed!')
                self.changes_made_to_assembly = True
            else:
                print('Not proceeding!')
                return
                
        # MAIN "DISAGGREGATE" ALGORITHM
        # ---
        # Get valid ID for new node then create
        no_disagg = 2
        for i in range(no_disagg):
            new_id   = self.create_new_id()
            new_node = self.assembly.tree.create_node(tag = self.new_part_text, parent = id_, identifier = new_id)
            print('New assembly ID = ', new_node.identifier)
            self.assembly.tree_dict[new_node.identifier] = self.new_part_text
        
        # Propagate changes
        self.ClearGUIItems()
        self.OnTreeCtrlChanged()
    
    
    
    def OnAggregate(self, event = None):

        # Check selected items are present and suitable
        if not self.selected_items_check():
            print('No items selected')
            return
        
        # Further checks
        if len(self.selected_items) == 1:
            id_ = self.ctc_dict_inv[self.selected_items[-1]]
            if id_ not in self.assembly.leaf_ids:
                print('ID of item to aggregate = ', id_)
            else:
                print('Cannot aggregate: item is a leaf node/irreducible part\n')
                return
        else:
            print('Cannot aggregate: more than one item selected\n')
            return

        # Check with user whether to proceed, as link to STEP file will be lost
        if not self.changes_made_to_assembly:
            caption = 'Aggregate sub-assembly?'
            message = 'Do you want to modify the assembly? Previous assembly will be retained'
    
            if self.okay_to_proceed(message, caption):
                print('Okay to proceed!')
                self.changes_made_to_assembly = True
            else:
                print('Not proceeding!')
                return

        # MAIN "AGGREGATE" ALGORITHM
        # ---
        # Get children of node and remove
        children_ = [el.identifier for el in self.assembly.tree.children(id_)]
        print('Children aggregated: ', children_)
        for el in children_:
            self.assembly.tree.remove_node(el)
        
        # Add list of children IDs as data for future reference
        # HR 6/3/20 WANT TO RETAIN CHILD NODES BY REMOVING EDGES
        # AND NOT BY REMOVING ENTIRELY: IMPLEMENT LATER IN NETWORKX
        self.assembly.tree.nodes[id_].data = children_
        
        
        # Propagate changes
        self.ClearGUIItems()
        self.OnTreeCtrlChanged()

    
    
    def OnAddNode(self, event = None):

        # Check selected items are present and suitable
        if not self.selected_items_check():
            print('No items selected')
            return
        
        # Further checks
        if len(self.selected_items) == 1:
            id_ = self.ctc_dict_inv[self.selected_items[-1]]
            if id_ not in self.assembly.leaf_ids:
                print('ID of item to add node to = ', id_)
            else:
                print('Cannot add node: item is a leaf node/irreducible part\n')
                print('To add node, disaggregate part first\n')
                return
        else:
            print('Cannot add node: more than one item selected\n')
            return

        # Check with user whether to proceed, as link to STEP file will be lost
        if not self.changes_made_to_assembly:
            caption = 'Add node to sub-assembly?'
            message = 'Do you want to modify the assembly? Previous assembly will be retained'
    
            if self.okay_to_proceed(message, caption):
                print('Okay to proceed!')
                self.changes_made_to_assembly = True
            else:
                print('Not proceeding!')
                return

        # MAIN "ADD NODE" ALGORITHM
        # ---
        # Create new node with selected item as parent
        new_id = self.create_new_id()
        new_node = self.assembly.tree.create_node(tag = self.new_part_text, parent = id_, identifier = new_id)
        print('New node ID = ', new_node.identifier)
        self.assembly.tree_dict[new_node.identifier] = self.new_part_text
        
        # Propagate changes
        self.ClearGUIItems()
        self.OnTreeCtrlChanged()
        
    
    
    def OnRemoveNode(self, event = None):

        # Check selected items are present and suitable
        if not self.selected_items_check():
            print('No items selected')
            return
        
        # Further checks
        self.selected_list = []
        if len(self.selected_items) >= 1:
            print('Selected item(s) to remove:\n')
            for item in self.selected_items:
                id_ = self.ctc_dict_inv[item]
                print('ID = ', id_)
                self.selected_list.append(id_)
        else:
            print('Cannot remove: no items selected\n')
            return
        
        # Check root is not present in selected items
        if self.assembly.tree.root in self.selected_list:
            print('Cannot remove: item(s) to remove include root')
            return
         
        # Check with user whether to proceed, as link to STEP file will be lost
        if not self.changes_made_to_assembly:
            caption = 'Remove item(s)?'
            message = 'Do you want to modify the assembly? Previous assembly will be retained'

            if self.okay_to_proceed(message, caption):
                print('Okay to proceed!')
                self.changes_made_to_assembly = True
            else:
                print('Not proceeding!')
                return
                
        # MAIN "REMOVE NODE" ALGORITHM
        # ---
        
        # Delete all selected nodes
        # Try/except block as some may have been removed earlier if further up tree
        for el in self.selected_list:
            try:
                self.assembly.tree.remove_node(el)
                print('Node ', el, ' removed')
            except:
                pass
        
        # Propagate changes
        self.ClearGUIItems()
        self.OnTreeCtrlChanged()



    def sort_check(self):
        
        # Check only one non-part item selected
        # ---
        # If-else/pass return block, for funs
        if hasattr(self, 'selected_items'):
            pass
        else:
            print('No assembly present')
            return
        
        if len(self.partTree_ctc.GetSelections()) == 1:
            pass
        else:
            print('No or more than one item(s) selected')
            return

        item = self.partTree_ctc.GetSelection()
        if item.HasChildren():
            pass
        else:
            print('Item is leaf node, cannot sort')
            return
        
        children_count = item.GetChildrenCount(recursively = False)
        if children_count > 1:
            pass
        else:
            print('Cannot sort: item has single child')
            return
        
        return True



    def OnSortTool(self, event):
        
        if self.sort_check():
            item = self.partTree_ctc.GetSelection()
        else:
            return
        
        # Toggle sort mode, then sort
        if self.partTree_ctc.alphabetical:
            self.partTree_ctc.alphabetical = False
        else:
            self.partTree_ctc.alphabetical = True
        self.partTree_ctc.SortChildren(item)
        
    
    
    def OnSortReverseTool(self, event):
        
        if self.sort_check():
            item = self.partTree_ctc.GetSelection()
        else:
            return
        
        # Toggle sort mode, then sort
        if self.partTree_ctc.reverse_sort:
            self.partTree_ctc.reverse_sort = False
        else:
            self.partTree_ctc.reverse_sort = True
        self.partTree_ctc.SortChildren(item)



    def OnSortAlpha(self, event = None):
        
        # Sort children of selected items alphabetically
        item = self.partTree_ctc.GetSelection()
        self.partTree_ctc.alphabetical = True
        self.partTree_ctc.SortChildren(item)
        
       
        
    def OnSortByID(self, event = None):
        
        # Sort children of selected item by ID
        item = self.partTree_ctc.GetSelection()
        
        # First reset "sort_id" as can be changed by drap and drop elsewhere
        # ---
        # MUST create shallow copy here to avoid strange behaviour
        # According to ctc docs, "It is advised not to change this list
        # [i.e. returned list] and to make a copy before calling
        # other tree methods as they could change the contents of the list."
        children = item.GetChildren().copy()
        for child in children:
            data = self.partTree_ctc.GetPyData(child)
            data['sort_id'] = data['id_']
            
        self.partTree_ctc.alphabetical = False
        self.partTree_ctc.SortChildren(item)

        
        
    def OnTreeDrag(self, event):
        
        # Drag and drop events are vetoed by default
        event.Allow()
        self.tree_drag_item = event.GetItem()
        id_ = self.ctc_dict_inv[event.GetItem()]
        print('ID of drag item = ', id_)
        self.tree_drag_id = id_
        
        
        
    def OnTreeDrop(self, event):
          
        # Allow event: drag and drop events vetoed by default
        event.Allow()
        
        drop_item = event.GetItem()
        id_ = self.ctc_dict_inv[drop_item]
        print('ID of item at drop point = ', id_)
     
        drag_parent = self.tree_drag_item.GetParent()
        drop_parent = drop_item.GetParent()
        
        # Check if root node involved; return if so
        if (not drag_parent) or (not drop_parent):
            print('Drag or drop item is root: cannot proceed')
            return

        # Check with user whether to proceed, as link to STEP file will be lost
        if not self.changes_made_to_assembly:
            caption = 'Move item(s)?'
            message = 'Do you want to modify the assembly? Previous assembly will be retained'

            if self.okay_to_proceed(message, caption):
                print('Okay to proceed!')
                self.changes_made_to_assembly = True
            else:
                print('Not proceeding!')
                return
            
        # CASE 1: DRAG AND DROP ITEMS HAVE THE SAME PARENT: MODIFY SORT ORDER
        # ---
        # If so, prepare sibling items by changing "sort_id" in part tree data
        # ---
        # HR 17/03/20: WHOLE SECTION NEEDS REWRITING TO BE SHORTER AND MORE EFFICIENT
        # PROBABLY VIA A FEW LIST OPERATIONS
        if drop_parent == drag_parent:
            
            sort_id = 1
            (child_, cookie_) = self.partTree_ctc.GetFirstChild(drop_parent)
            
            # If drop item found, slip drag item into its place
            if child_ == drop_item:
                self.partTree_ctc.GetPyData(self.tree_drag_item)['sort_id'] = sort_id
                sort_id += 1
            elif child_ == self.tree_drag_item:
                pass
            else:
                self.partTree_ctc.GetPyData(child_)['sort_id'] = sort_id
                sort_id += 1

            child_ = self.partTree_ctc.GetNextSibling(child_)
            while child_:
                
                # If drop item found, slip drag item into its place
                if child_ == drop_item:
                    self.partTree_ctc.GetPyData(self.tree_drag_item)['sort_id'] = sort_id
                    sort_id += 1
                elif child_ == self.tree_drag_item:
                    pass
                else:
                    self.partTree_ctc.GetPyData(child_)['sort_id'] = sort_id
                    sort_id += 1
                child_ = self.partTree_ctc.GetNextSibling(child_)

            # Resort, then return to avoid redrawing part tree otherwise
            self.partTree_ctc.alphabetical = False
            self.partTree_ctc.SortChildren(drop_parent)
            return
        
        # CASE 2: DRAG AND DROP ITEMS DO NOT HAVE THE SAME PARENT: SIMPLE MOVE
        # ---
        # Drop item is sibling unless it's root, then it's parent
        if self.assembly.tree.parent(id_):
            parent = self.assembly.tree.parent(id_)
            parent = parent.identifier
        else:
            parent = id_
        self.assembly.tree.move_node(self.tree_drag_id, parent)

        # Propagate changes
        self.ClearGUIItems()
        self.OnTreeCtrlChanged()

        
        
    def OnTreeLabelEditEnd(self, event):
        
        # Propagate label text to other objects
        # HR 21/02/20 THIS SHOULD BE IMPROVED TO CHECK WHETHER TEXT HAS ACTUALLY
        # CHANGED USING EXTRA BINDING TO BEGIN-EDIT EVENT
        # ---
        
        # Check with user whether to proceed, as link to STEP file will be lost
        if not self.changes_made_to_assembly:
            caption = 'Change item label information?'
            message = 'Do you want to modify the item label? Previous assembly will be retained'

            if self.okay_to_proceed(message, caption):
                print('Okay to proceed!')
                self.changes_made_to_assembly = True
            else:
                print('Not proceeding!')
                event.Veto()
                return

        wx.CallAfter(self.AfterTreeLabelEdit, event)
        event.Skip()
        
        
        
    def AfterTreeLabelEdit(self, event):
        
        item_ = event.GetItem()
        id_   = self.ctc_dict_inv[item_]
        text_ = item_.GetText()
        
        # Tree object
        self.assembly.tree.update_node(id_, tag = text_)
        # Lattice object
        self.assembly.g.nodes[id_]['label'] = text_
        
        
        
    def ClearGUIItems(self):
        
        # Destroy all button objects
        for button_ in self.button_dict:
            obj = self.button_dict[button_]
            obj.Destroy()
            
        # Clear all relevant lists/dictionaries
        self.ctc_dict.clear()
        self.ctc_dict_inv.clear()

        self.checked_items.clear()
        self.selected_items.clear()
        
        self.button_dict.clear()
        self.button_dict_inv.clear()
        self.button_img_dict.clear()

       
           
    def selected_items_check(self):
        
        # Return false if no items selected or (e.g.) no file loaded
        if hasattr(self, 'selected_items'):
            if self.selected_items:
                return True
            else:
                return False
        else:
            return False



    def okay_to_proceed(self, message = 'Dialog', caption = 'Okay to proceed?', style = wx.OK | wx.CANCEL):
        
        # Dialogue to return true if user clicks "OK"
        okay = wx.MessageDialog(self, message = message, caption = caption, style = style)
        answer = okay.ShowModal()
        if answer == wx.ID_OK:
            return True
        okay.Destroy()



    def OnAbout(self, event):

        # Show program info
        abt_text = """StrEmbed-5-2: A user interface for manipulation of design configurations\n
            Copyright (C) 2019-2020 Hugh Patrick Rice\n
            This research is supported by the UK Engineering and Physical Sciences
            Research Council (EPSRC) under grant number EP/S016406/1.\n
            This program is free software: you can redistribute it and/or modify
            it under the terms of the GNU General Public License as published by
            the Free Software Foundation, either version 3 of the License, or
            (at your option) any later version.\n
            This program is distributed in the hope that it will be useful,
            but WITHOUT ANY WARRANTY; without even the implied warranty of
            MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
            GNU General Public License for more details.\n
            You should have received a copy of the GNU General Public License
            along with this program. If not, see <https://www.gnu.org/licenses/>."""
 
        abt = wx.MessageDialog(self, abt_text, 'About StrEmbed-5-2', wx.OK)
        # Show dialogue that stops process (modal)
        abt.ShowModal()
        abt.Destroy()



    def OnResize(self, event):

        # Display window size in status bar
        self.statbar.SetStatusText("Window size = " + format(self.GetSize()))
        wx.CallAfter(self.AfterResize, event)
        event.Skip()
        
        
        
    def AfterResize(self, event = None):
        
        # Resize all images in geometry view
        if not hasattr(self, 'file_open'):
            return
        if self.file_open:
            # Get size of grid element
            width_ = self.geom_panel.GetSize()[0]/self.image_cols
            for k, v in self.button_dict.items():
                img    = self.button_img_dict[k]
                img_sc = self.ScaleImage(img, width_)
                v.SetBitmap(wx.Bitmap(self.ScaleImage(img_sc)))
                
            self.geom_panel.SetupScrolling(scrollToTop = False)

        

    def MouseMoved(self, event):
        
        # Display mouse coordinates (panel and absolute) upon movement
        self.panel_pos  = event.GetPosition()
        self.screen_pos = wx.GetMousePosition()
        self.statbar.SetStatusText("Pos in panel = " + format(self.panel_pos) +
                                   "; Screen pos = " + format(self.screen_pos))
        event.Skip()



    def DoNothingDialog(self, event):

        nowt = wx.MessageDialog(self, "Functionality to be added", "Do nothing dialog", wx.OK)
        # Create modal dialogue that stops process
        nowt.ShowModal()
        nowt.Destroy()



    def OnExit(self, event):

        # Close program
        self.Close(True)

        

if __name__ == '__main__':
    app = wit.InspectableApp()
    frame = MainWindow()
    frame.Show()
    frame.Maximize()
    app.MainLoop()