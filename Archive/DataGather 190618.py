'''
Data gathering app - to record various data from instruments and display it in graphical form 

More functionality will be added as we go on

Gregor Taylor - June 2018

'''

import sys
import time
import os
import csv
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2TkAgg
from matplotlib.figure import Figure
#Ensure works on both Python 2 and 3, tkinter imports vary
if sys.version[0] == '3':
    from tkinter import *
    from tkinter import ttk
    from tkinter.filedialog import askopenfilename
    from tkinter import simpledialog
    from tkinter import messagebox
elif sys.version[0] == '2':
    from Tkinter import *
    import ttk
    from tkFileDialog import askopenfilename 
    import tkSimpleDialog as simpledialog
    import tkMessageBox as messagebox
from visa import *
import ThorlabsPM100
from hardware import SIM900
import numpy as np

#Def font for labels   
LARGE_FONT= ("Verdana", 12)

###TESTING DELETE WHEN DONE
#example_list = ["12321412.4124.12412", "USB2", "ASLR1"]
#TESTING_filename = "Z:\\User folders\\Gregor Taylor\\MIR work\\OPO\\Thu_Jun_07_13_35_29_2018_power_vs_temp_1um_in_opo_v_tcouple_int.txt"

###
#Main Class
###
class DataGatheringapp(Tk):

    def __init__(self, *args, **kwargs):
        
        
        Tk.__init__(self, *args, **kwargs)
        
        Tk.wm_title(self, "Data Gathering")

        self.instr_address_dict = {}
        self.SIM_slots = {}
        self.headers = ['Time']
        self.plot_arrays_dict = {}
        self.plot_col_dict = {}
        self.to_plot=[]
        self.plot_keys={"Amb_Pwr": [1,2,3], "Pwr_Only": [3]}
        self.measurement_after_id = None
        self.Filename = ''
        self.rm = ResourceManager()
        
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand = True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        #frames hold the app pages
        self.frames = {}
        #all page must be added to following tuple
        for F in (StartPage, MeasTypePage,ValuesTimePage, WorkingPage, GraphSetupPage, DisplayGraphPage):
            frame=F(container, self)
            self.frames[F] = frame
            #defines the grid
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(StartPage)

    def show_frame(self, cont):
        #Raises the chosen page to the top.
        frame = self.frames[cont]
        if cont == DisplayGraphPage:
            frame.event_generate("<<ShowGraphPage>>")
        frame.tkraise()
        
###
#Startup pages
###
class StartPage(ttk.Frame):
    def __init__(self, parent, controller): 
        Frame.__init__(self,parent)
        self.get_devices(controller)

        label = ttk.Label(self, text="Select what you want to gather data from:", font=LARGE_FONT)
        label.grid(row=1,column=1,padx=20)
        
        ttk.Label(self, text="Power meter:").grid(row=2,column=1)
        pwr_meter_add=ttk.Combobox(self, values=self.dev_list)
        pwr_meter_add.grid(row=2,column=2)
        
        ttk.Label(self, text="SIM900:").grid(row=3,column=1)
        sim900_add=ttk.Combobox(self, values=self.dev_list)
        sim900_add.grid(row=3,column=2)
        
        ttk.Label(self, text="Optical attenuator 1:").grid(row=4,column=1)
        opat1_add=ttk.Combobox(self, values=self.dev_list)
        opat1_add.grid(row=4,column=2)
        
        ttk.Label(self, text="Optical attenuator 2:").grid(row=5,column=1)
        opat2_add=ttk.Combobox(self, values=self.dev_list)
        opat2_add.grid(row=5,column=2)
        
        ttk.Label(self, text="Pulse Counter:").grid(row=6,column=1)
        pulse_add=ttk.Combobox(self, values=self.dev_list)
        pulse_add.grid(row=6,column=2)
        #button OKs and extracts values from combobox'
        ok_button = ttk.Button(self, text="Confirm", command=lambda:self.get_addresses(controller, pwr_meter_add.get(), sim900_add.get(), 
                                                                                       opat1_add.get(), opat2_add.get(), pulse_add.get()))
        ok_button.grid(row=7,column=2)

        refresh_button = ttk.Button(self, text="Refresh devices", command=lambda:self.get_devices(controller))
        refresh_button.grid(row=7, column=1)
    
    def get_addresses(self, controller, pwr_meter_add, sim900_add, opat1_add, opat2_add, pulse_add):
        controller.instr_address_dict["power_m_address"] = pwr_meter_add
        controller.instr_address_dict["sim900_address"] = sim900_add
        controller.instr_address_dict["opat1_address"] = opat1_add
        controller.instr_address_dict["opat2_address"] = opat2_add
        controller.instr_address_dict["pulse_c_address"] = pulse_add
        controller.show_frame(MeasTypePage)

    def get_devices(self, controller):
        self.dev_list = controller.rm.list_resources()
        
    
#Page to select measurement type - more will be added.        
class MeasTypePage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self,parent)
        label = ttk.Label(self, text="Select what type of measurement you want to do:", font=LARGE_FONT)
        label.grid(row=1,column=1,padx=20)
        
        ttk.Button(self, text="Values against time", command=lambda: controller.show_frame(ValuesTimePage)).grid(row=2,column=1)

###
#Specific values v time pages
###
        
class ValuesTimePage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self,parent)
        label = ttk.Label(self, text="Enter connection config:", font=LARGE_FONT)
        label.grid(row=1,column=1,padx=20)
        
        ttk.Label(self, text="Voltage source slot?:").grid(row=2,column=1)
        VSource_slot = ttk.Entry(self)
        VSource_slot.grid(row=2,column=2)
        
        ttk.Label(self, text="Voltmeter slot?:").grid(row=3,column=1)
        VMeter_slot = ttk.Entry(self)
        VMeter_slot.grid(row=3,column=2)
        
        ttk.Label(self, text="Number of voltmeter connections? (Connect them in order...):").grid(row=4,column=1)
        VMeter_num = ttk.Entry(self)
        VMeter_num.grid(row=4,column=2)
        
        ttk.Label(self, text="Thermometer slot?:").grid(row=5,column=1)
        Therm_slot = ttk.Entry(self)
        Therm_slot.grid(row=5,column=2)
        
        ok_button=ttk.Button(self, text="Confirm", command=lambda: self.confirm_connections(controller, VSource_slot.get(), VMeter_slot.get(),
                                                                                            VMeter_num.get(), Therm_slot.get()))
        ok_button.grid(row=6, column=2)


    def confirm_connections(self, controller, VSource_slot, VMeter_slot, VMeter_num, Therm_slot):
        if VMeter_slot != '':
            try:
                controller.SIM_slots["VSource"] = VSource_slot
                controller.SIM_slots["VMeter"] = VMeter_slot
                controller.SIM_slots["ThermSlot"] = Therm_slot
                controller.SIM_slots["NumberOfVMeters"] = int(VMeter_num)
                self.setup_data_gather(controller)
                controller.show_frame(WorkingPage)                
            except ValueError:
                messagebox.showerror('Error', 'Enter a valid number of voltmeters')
                controller.show_frame(ValuesTimePage)
        else:
            controller.SIM_slots["VSource"] = VSource_slot
            controller.SIM_slots["VMeter"] = VMeter_slot
            controller.SIM_slots["ThermSlot"] = Therm_slot
            self.setup_data_gather(controller)
            controller.show_frame(WorkingPage)
            
    def setup_data_gather(self, controller):
        #sets up header data and connects all isntruments required
        controller.Filename = os.path.dirname(os.path.abspath(__file__))+"\\Data\\"+time.ctime().replace(" ", "_").replace(":","_")
        if controller.SIM_slots['ThermSlot'] != '':
            controller.headers+['T1', 'T2', 'T3']
            controller.Filename+='_temp'
        if controller.SIM_slots['VSource'] != '':
            controller.headers.append('V_Source(V)')
            controller.Filename+='_VSrc'
        if controller.SIM_slots['VMeter'] != '':
            controller.Filename+='_VMeas'
            for i in range(controller.SIM_slots['NumberOfVMeters']):
                controller.headers.append('V_'+str(i+1)+'(V)')
        if controller.instr_address_dict['power_m_address'] != '':
            controller.headers.append('Power(W)')
            controller.Filename+='_power'
            #setup pwr meter connection
            pwr_m_address = controller.rm.open_resource(controller.instr_address_dict['power_m_address']) #put this in one line
            controller.PM100 = ThorlabsPM100.ThorlabsPM100(inst=pwr_m_address)
        if controller.instr_address_dict['pulse_c_address'] != '':
            controller.headers.append('Counts')
            controller.Filename+='_counts'
            #setup pulse counter connection
            controller.PCounter = ResourceManager.open_resource(controller.instr_address_dict['pulse_c_address'])
        #PRINT HEADERS TO FILE#
        controller.Filename+='.txt'
        try:
            os.makedirs(os.path.dirname(controller.Filename))
        except OSError:
           pass
        with open(controller.Filename, 'a+') as file_handle:
            writer_csv =  csv.writer(file_handle, delimiter=',')
            writer_csv.writerow(controller.headers)
        
        #setup connections to SIM9000 if required
        if (controller.SIM_slots['ThermSlot'],controller.SIM_slots['VMeter'], controller.SIM_slots['VSource']) != ('','',''):
            controller.sim900 = SIM900(controller.instr_address_dict['sim900_address'])

class WorkingPage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        label=ttk.Label(self, text = "Working!", font=LARGE_FONT)
        label.grid(row=1,column=1)
        
        start_meas_button = Button(self, text="Start measuring", command=lambda: self.get_dataset(controller))
        start_meas_button.grid(row=2,column=1)
        
        stop_meas_button = Button(self, text="Stop measuring", command=lambda:self.stop_meas(controller))
        stop_meas_button.grid(row=3,column=1)

        graph_button = Button(self, text="Graph", command=lambda: self.graph_it(controller))
        graph_button.grid(row=4,column=1)

        self.size_label=ttk.Label(self, text= ("File size = 0 bytes"))#MIGHT NEED SELF HERE
        self.size_label.grid(row=5,column=1)

        load_file_button = Button(self, text="Load other data file", command=lambda:self.load_other_file(controller))
        load_file_button.grid(row=6,column=1)


    def get_dataset(self, controller):#removed size_label
        if controller.measurement_after_id == None:
            self.start_time_meas = time.time()
        #Always time
        data_to_write = [str(time.time()-self.start_time_meas)]
        #Other applicable data
        for i in controller.headers[1:]:
            if i == ['T1', 'T2', 'T3']:
                t1 = str(controller.sim900.ask(controller.SIM_slots['ThermSlot'],'TVAL? 1')).strip()
                t2 = str(controller.sim900.ask(controller.SIM_slots['ThermSlot'],'TVAL? 2')).strip()
                t3 = str(controller.sim900.ask(controller.SIM_slots['ThermSlot'],'TVAL? 3')).strip()
                data_to_write += [t1,t2,t3]
            if i == 'V_Source(V)':
                data_to_write.append(str(controller.sim900.ask(controller.SIM_slots['VSource'],'VOLT?')).strip()) # not sure correct
            if i == 'Power(W)':
                data_to_write.append(str(controller.PM100.read).strip())
            if i == 'Counts':
                data_to_write.append('x')#Wont do counts yet
            if i == 'V_1(V)':
                data_to_write.append(str(controller.sim900.ask(controller.SIM_slots['VMeter'],'VOLT? 1,1')).strip())
            if i == 'V_2(V)':
                data_to_write.append(str(controller.sim900.ask(controller.SIM_slots['VMeter'],'VOLT? 2,1')).strip())
            if i == 'V_3 (V)':
                data_to_write.append(str(controller.sim900.ask(controller.SIM_slots['VMeter'],'VOLT? 3,1')).strip())
            if i == 'V_4 (V)':
                data_to_write.append(str(controller.sim900.ask(controller.SIM_slots['VMeter'],'VOLT? 4,1')).strip())
        with open(controller.Filename, 'a+') as file_handle:
            writer_csv =  csv.writer(file_handle, delimiter=',')
            writer_csv.writerow(data_to_write)
        self.size_label['text'] = "File size = "+str(os.path.getsize(controller.Filename))+" bytes"
        controller.measurement_after_id = app.after(1000, self.get_dataset, controller)
                
    def stop_meas(self, controller):
        app.after_cancel(controller.measurement_after_id)
        controller.measurement_after_id = None
     
    def graph_it(self, controller):
        if controller.measurement_after_id != None:
            messagebox.showerror('Error', 'Measurement still running')
        else:
            controller.show_frame(GraphSetupPage)

    def load_other_file(self, controller):
        controller.Filename = askopenfilename(initialdir="Z:\\", title="Choose a file")
        self.size_label['text'] = "File size = "+str(os.path.getsize(controller.Filename))+" bytes"




    #TO DO 

class GraphSetupPage(ttk.Frame):
    #NEED TO CHANGE WAY WHATS DECIDED WHAT IS PLOTTED - Will only work for amb temp and power.
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)

        pall_button = ttk.Button(self, text='Plot all parameters', command=lambda: self.configure_plot(controller, "Amb_Pwr"))###DUMMY KEY
        pall_button.grid(row=1,column=1)

        pwr_button = ttk.Button(self, text='Plot power only', command=lambda: self.configure_plot(controller, "Pwr_Only"))
        pwr_button.grid(row=2,column=1)

    def read_time_and_cols(self, controller):
        titles_list=[]

        with open(controller.Filename) as csv_file:
            read_csv = csv.reader(csv_file, delimiter=',')
            for index, row in enumerate(read_csv):
                if len(row)>0:
                    if index==0:
                        for i in row:
                            titles_list.append(i)
                        number_cols = len(titles_list)
                        for i in range(number_cols):
                            controller.plot_col_dict[i]=[]
                    else:
                        for i in range(number_cols):
                            controller.plot_col_dict[i].append(row[i])
#convert time to to arrays
        controller.plot_time_arr = np.asarray(controller.plot_col_dict[0], dtype='float')
        for i in range(number_cols):
            if i == 0:
                pass
            else:
                controller.plot_arrays_dict[i]=np.asarray(controller.plot_col_dict[i], dtype='float')

    def configure_plot(self, controller, pl_type):
        self.read_time_and_cols(controller)
        controller.plot_type = pl_type
        controller.show_frame(DisplayGraphPage)


class DisplayGraphPage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.graph_set = False
        self.bind("<<ShowGraphPage>>", lambda event:self.on_show_graph_page(controller))
        self.VvT_graph= Figure(figsize=(1,1), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.VvT_graph, self) 
        self.canvas.get_tk_widget().pack(side="bottom", fill="both", expand = True)
        self.toolbar = NavigationToolbar2TkAgg(self.canvas, self)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side="top", fill="both", expand = True)

        return_button = ttk.Button(self, text="Return to data gathering", command=lambda: controller.show_frame(WorkingPage))
        return_button.pack()


    def on_show_graph_page(self, controller):
        #NEED TO DESTROY FIG
        if self.graph_set == True:
            self.VvT_graph.clear()
            self.graph_set = False
        controller.to_plot = controller.plot_keys[controller.plot_type]
        sp1_1 = self.VvT_graph.add_subplot(111)
        if controller.plot_type == "Pwr_Only":
            sp1_1.plot(controller.plot_time_arr,controller.plot_arrays_dict[controller.to_plot[0]], 'g-')
            sp1_1.set_xlabel('Time (s)')
            sp1_1.set_ylabel('Power (W)')

        elif controller.plot_type == "Amb_Pwr":
            sp1_1.plot(controller.plot_time_arr, controller.plot_arrays_dict[controller.to_plot[0]], 'b-')
            sp1_1.plot(controller.plot_time_arr, controller.plot_arrays_dict[controller.to_plot[1]], 'r-')
            sp1_1.set_xlabel('Time (s)')
            sp1_1.set_ylabel('Voltage (V)')
            
            sp1_2=sp1_1.twinx()
            sp1_2.plot(controller.plot_time_arr, controller.plot_arrays_dict[controller.to_plot[2]], 'g-')
            sp1_2.set_ylabel('Power (W)')
        self.graph_set = True
        self.canvas.draw()

   
 
app = DataGatheringapp()
app.geometry("700x300")
app.mainloop()

