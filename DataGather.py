'''
Data gathering app for common SNSPD characterisation

Functionality:
-Gather data from connected instruments (pwr_meters, SIM900 vmeters/vsrcs/thermometers etc) and plot them against time
-Perform efficiency measurements 
-Perform dark count rate measurements
-Perform resistance-temperature measurements to determine critical temperature
-Can be used to plot data files that have been created with this program

More functionality will be added as we go on

Gregor Taylor - June 2018

'''

##############################################################################
#Imports and Setup
##############################################################################

import sys
import time
import os
import csv
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from matplotlib import style
from cycler import cycler
from tkinter import *
from tkinter import ttk
from tkinter.filedialog import askopenfilename
from tkinter import simpledialog
from tkinter import messagebox
from visa import *
import ThorlabsPM100
from hardware import SIM900
import numpy as np
from ExceptionLogger import exception_logger

#Define font for labels   
LARGE_FONT= ("Verdana", 12)
#Define plot style
style.use('ggplot')
##############################################################################
#Main Class
##############################################################################

class DataGatheringapp(Tk):
    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        Tk.iconbitmap(self, default="UD_Smiley.ico")
        Tk.wm_title(self, "Data Gathering")
        #Data holders
        self.instr_address_dict = {}
        self.SIM_slots = {}
        self.headers = ['Time']
        self.plot_arrays_dict = {}
        self.plot_col_dict = {}
        self.measurement_after_id = None    #ID to keep track of measurements running
        self.Filename = ''
        self.rm = ResourceManager()    #Pyvisa resource manager

        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand = True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        #Frames hold the app pages
        self.frames = {}
        #all page must be added to following tuple
        for F in (StartPage, MeasTypePage,ValuesTimePage, WorkingPage, DisplayGraphPage, EDPSetupPage, EfficiencyPage, DCRPage, PlotExistingFilePage, RTPage):
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
        
##############################################################################
#Add instruments
##############################################################################

class StartPage(ttk.Frame):
    def __init__(self, parent, controller): 
        Frame.__init__(self,parent)
        self.get_devices(controller)    #Populates device list with connected instr

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

        existing_file_butt = ttk.Button(self, text="Plot a pre-existing data file", command=lambda:controller.show_frame(PlotExistingFilePage))
        existing_file_butt.grid(row=8,column=1)
    
    def get_addresses(self, controller, pwr_meter_add, sim900_add, opat1_add, opat2_add, pulse_add):
        controller.instr_address_dict["power_m_address"] = pwr_meter_add
        controller.instr_address_dict["sim900_address"] = sim900_add
        controller.instr_address_dict["opat1_address"] = opat1_add
        controller.instr_address_dict["opat2_address"] = opat2_add
        controller.instr_address_dict["pulse_c_address"] = pulse_add
        controller.show_frame(MeasTypePage)

    def get_devices(self, controller):
        self.dev_list = controller.rm.list_resources()
        
    
##############################################################################
#Select measurement page
##############################################################################

class MeasTypePage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self,parent)
        label = ttk.Label(self, text="Select what type of measurement you want to do:", font=LARGE_FONT)
        label.grid(row=1,column=1,padx=20)
        
        ttk.Button(self, text="RT measurement or generic values against time", command=lambda: controller.show_frame(ValuesTimePage)).grid(row=2,column=1)

        ttk.Button(self, text="Efficiency/DCR/PCR", command=lambda: self.go_to_EDP_page(controller)).grid(row=3,column=1)

        ttk.Button(self, text="Go back to instrument setup page", command=lambda: controller.show_frame(StartPage)).grid(row=5,column=1)

    def go_to_EDP_page(self, controller):
        if controller.instr_address_dict["pulse_c_address"] == '':
            messagebox.showerror('Error', 'No pulse counter given - go back and find one')
        elif controller.instr_address_dict["opat1_address"] == '':
            messagebox.showinfo('Warning!', 'No attenuator found - must be doing manual attenuation')
            controller.manual_atten = True
            controller.show_frame(EDPSetupPage)
        else:
            controller.manual_atten = False
            controller.show_frame(EDPSetupPage)


##############################################################################
#Gather values vs time setup page
##############################################################################
        
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

        ttk.Button(self, text="Go back to measurement choice page", command=lambda: controller.show_frame(MeasTypePage)).grid(row=6,column=1)
        


    def confirm_connections(self, controller, VSource_slot, VMeter_slot, VMeter_num, Therm_slot):
        if VMeter_slot != '':
            try:
                controller.SIM_slots["VSource"] = VSource_slot
                controller.SIM_slots["VMeter"] = VMeter_slot
                controller.SIM_slots["ThermSlot"] = Therm_slot
                controller.SIM_slots["NumberOfVMeters"] = int(VMeter_num)
                controller.show_frame(WorkingPage)                
            except ValueError:
                messagebox.showerror('Error', 'Enter a valid number of voltmeters')
                controller.show_frame(ValuesTimePage)
        else:
            controller.SIM_slots["VSource"] = VSource_slot
            controller.SIM_slots["VMeter"] = VMeter_slot
            controller.SIM_slots["ThermSlot"] = Therm_slot
            controller.show_frame(WorkingPage)

##############################################################################
#Gather values vs time data page
##############################################################################

class WorkingPage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        ttk.Label(self, text="Enter number of power values to average over (required for small powers, leave blank for default):").grid(row=1,column=1)
        av_pwr = ttk.Entry(self)
        av_pwr.grid(row=1,column=2)

        ttk.Label(self,text="Enter wavelength of interest:").grid(row=2,column=1)
        wav_pwr = ttk.Entry(self)
        wav_pwr.grid(row=2,column=2)
        
        start_meas_button = ttk.Button(self, text="Start measuring", command=lambda: self.setup_data_gather(controller, av_pwr.get(),wav_pwr.get()))
        start_meas_button.grid(row=3,column=1)
        
        stop_meas_button = ttk.Button(self, text="Stop measuring", command=lambda:self.stop_meas(controller))
        stop_meas_button.grid(row=4,column=1)

        graph_button = ttk.Button(self, text="Graph", command=lambda: self.graph_it(controller))
        graph_button.grid(row=5,column=1)

        self.size_label=ttk.Label(self, text= ("File size = 0 bytes"))#MIGHT NEED SELF HERE
        self.size_label.grid(row=6,column=1)

        RT_butt = ttk.Button(self, text='Go to RT measurement page', command=lambda: controller.show_frame(RTPage))
        RT_butt.grid(row=7,column=1)

        ttk.Button(self, text="Go back to measurement choice page", command=lambda: controller.show_frame(MeasTypePage)).grid(row=8,column=1)


    def setup_data_gather(self, controller, av_pwr_count, wav_pwr):
        #sets up header data and connects all isntruments required
        controller.Filename = os.path.dirname(os.path.abspath(__file__))+"\\Data\\"+time.ctime().replace(" ", "_").replace(":","_")
        if controller.SIM_slots['ThermSlot'] != '':
            controller.headers+=['T1', 'T2', 'T3']
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
            controller.PM100.sense.correction.wavelength = int(wav_pwr)
            if av_pwr_count != '':
                controller.PM100.sense.average.count=int(av_pwr_count) #must be set for low powers
        if controller.instr_address_dict['pulse_c_address'] != '':
            controller.headers.append('Counts')
            controller.Filename+='_counts'
            #setup pulse counter connection
            controller.PCounter = controller.rm.open_resource(controller.instr_address_dict['pulse_c_address'])
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
        
        self.get_dataset(controller)



    def get_dataset(self, controller):
        if controller.measurement_after_id == None:
            self.start_time_meas = time.time()
        #Always time
        data_to_write = [str(time.time()-self.start_time_meas)]
        #Other applicable data
        for i in controller.headers[1:]:
            if i == 'T1':
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
        elif controller.Filename == None:
            messagebox.showerror('Error', 'No file to plot!')
        else:
            extract_data(controller, "VvT")
            controller.show_frame(DisplayGraphPage)

##############################################################################
#Display graph page
##############################################################################

class DisplayGraphPage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        #Sets up blank graph canvas
        self.axis_1_colours = ['r','g','b','y','navy']    #sets different colour cyclers for each axis to avoid confusion
        self.axis_2_colours = ['y','m','k','gray','greenyellow']
        self.graph_set = False
        self.bind("<<ShowGraphPage>>", lambda event:self.on_show_graph_page(controller))
        self.VvT_graph= Figure(figsize=(1,1), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.VvT_graph, self) 
        self.canvas.get_tk_widget().pack(side="bottom", fill="both", expand = True)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self)
        self.toolbar.update()
        self.canvas._tkcanvas.pack(side="top", fill="both", expand = True)

        return_button = ttk.Button(self, text="Return to home", command=lambda: controller.show_frame(StartPage))
        return_button.pack()    #Need to pack as one of the matplotlib funcs uses pack so cannot mix with grid
        return_button2=ttk.Button(self, text="Go back to measurement choice page", command=lambda: controller.show_frame(MeasTypePage))
        return_button2.pack()


    def on_show_graph_page(self, controller):
        if self.graph_set == True:    #This bit clears everything from the graph page everytime it's opened.
            controller.Y_index_list = []
            controller.Y2_index_list = []
            self.VvT_graph.clear()    #Clears graph
            try:
                if self.select_atten_box.winfo_exists() == 1:
                    self.select_atten_box.destroy()    #Destroys widgets, needs the try, except for if they never existed.
            except AttributeError:
                pass
            try:
                if self.config_plot_butt.winfo_exists() == 1:
                    self.config_plot_butt.destroy()
                    self.plot_VvT_butt.destroy()
            except AttributeError:
                pass
            self.graph_set = False
        self.sp1_1 = self.VvT_graph.add_subplot(111)
        self.sp1_1.set_prop_cycle(cycler('color', self.axis_1_colours))
        #Plots data based on plot_type
        if controller.plot_type == 'VvT':
            self.config_plot_butt=ttk.Button(self, text="Configure columns", command=lambda: WhatToPlot(controller))
            self.config_plot_butt.pack(side=LEFT)
            self.plot_VvT_butt = ttk.Button(self, text="Plot it", command=lambda: self.plot_VvT(controller))
            self.plot_VvT_butt.pack(side=RIGHT)
        elif controller.plot_type == 'DCR':
            self.sp1_1.plot(controller.plot_arrays_dict[2],controller.plot_arrays_dict[3], 'ko', markersize=2)
            self.sp1_1.set_yscale('log')
            self.sp1_1.set_ylabel('Counts (CPS)')
            self.sp1_1.set_xlabel('Bias (A)')
            self.sp1_1.set_title('Counts vs Bias')
        elif controller.plot_type == 'EFF':
            self.select_atten_box=ttk.Combobox(self, values=list(controller.eff_dict.keys()))    #Can change plot depending on atten value selected
            self.select_atten_box.pack()
            self.select_atten_box.bind("<<ComboboxSelected>>", lambda event:self.eff_plot_update(controller))
        elif controller.plot_type == 'RT':
            self.sp1_1.plot(controller.plot_arrays_dict[2],controller.plot_arrays_dict[5], 'bo', markersize=2)
            self.sp1_1.set_ylabel('R (Ohm)')
            self.sp1_1.set_xlabel('T (K)')
            self.sp1_1.set_title('R-T')

        self.graph_set = True
        self.canvas.draw()
    
    def eff_plot_update(self, controller):
        atten = self.select_atten_box.get()
        self.VvT_graph.clear()
        sp1_1 = self.VvT_graph.add_subplot(111)
        sp1_1.plot(controller.bias_arr, controller.eff_dict[atten], 'r*')
        sp1_1.set_ylabel('Efficiency (%)')
        sp1_1.set_xlabel('Bias(uA)')
        sp1_1.set_title('Efficiency at '+atten+'dB attenuation')
        self.canvas.draw()

    def plot_VvT(self, controller):
        for i in controller.Y_index_list:
            self.sp1_1.plot(controller.plot_arrays_dict[controller.X_index], controller.plot_arrays_dict[i])
        self.sp1_1.set_xlabel(controller.data_titles[controller.X_index])
        self.sp1_1.set_ylabel(controller.data_titles[controller.Y_index_list[0]]) #This should grab the first title that was plotted and set it
        if controller.Y2_index_list != []:
            self.sp1_2=self.sp1_1.twinx()
            self.sp1_2.set_prop_cycle(cycler('color', self.axis_2_colours))
            for i in controller.Y2_index_list:
                self.sp1_2.plot(controller.plot_arrays_dict[controller.X_index], controller.plot_arrays_dict[i])
            self.sp1_2.set_ylabel(controller.data_titles[controller.Y2_index_list[0]])
        self.canvas.draw()


##############################################################################
#Graph editing pop up
##############################################################################

class WhatToPlot(Toplevel):
    def __init__(self, controller):
        Toplevel.__init__(self)
        self.geometry("500x300")
        self.title("What do you want to plot?")
        XLabel = ttk.Label(self, text='X-axis', font=LARGE_FONT)
        XLabel.grid(row=1,column=1, padx=20)
        YLabel = ttk.Label(self, text='Y-axis ?', font=LARGE_FONT)
        YLabel.grid(row=1,column=2, padx=20)
        Y2Label = ttk.Label(self, text='Y-axis 2', font=LARGE_FONT)
        Y2Label.grid(row=1,column=3, padx=20)
        
        self.X=ttk.Combobox(self, values=controller.data_titles)
        self.X.grid(row=2, column=1)

        Y_1=ttk.Combobox(self, values=controller.data_titles)
        Y_1.grid(row=2,column=2)
        Y_2=ttk.Combobox(self, values=controller.data_titles)
        Y_2.grid(row=3,column=2)
        Y_3=ttk.Combobox(self, values=controller.data_titles)
        Y_3.grid(row=4,column=2)
        Y_4=ttk.Combobox(self, values=controller.data_titles)
        Y_4.grid(row=5,column=2)
        Y_5=ttk.Combobox(self, values=controller.data_titles)
        Y_5.grid(row=6,column=2)

        Y2_1=ttk.Combobox(self, values=controller.data_titles)
        Y2_1.grid(row=2,column=3)
        Y2_2=ttk.Combobox(self, values=controller.data_titles)
        Y2_2.grid(row=3,column=3)
        Y2_3=ttk.Combobox(self, values=controller.data_titles)
        Y2_3.grid(row=4,column=3)
        Y2_4=ttk.Combobox(self, values=controller.data_titles)
        Y2_4.grid(row=5,column=3)
        Y2_5=ttk.Combobox(self, values=controller.data_titles)
        Y2_5.grid(row=6,column=3)

        self.Y_obj_list = [Y_1, Y_2, Y_3, Y_4, Y_5]
        self.Y2_obj_list = [Y2_1, Y2_2, Y2_3, Y2_4, Y2_5]


        conf_butt = ttk.Button(self, text="Confirm and close", command=lambda: self.confirm_and_close(controller))
        conf_butt.grid(row=7, column=1, columnspan=2)

    def confirm_and_close(self, controller):
        controller.Y_index_list = self.check_vals(self.Y_obj_list, controller.data_titles)
        controller.Y2_index_list = self.check_vals(self.Y2_obj_list, controller.data_titles)
        controller.X_index = controller.data_titles.index(self.X.get())
        self.destroy()

    def check_vals(self, obj_list, data_titles):
        vals_list = []
        index_to_plot_list = []    
        for o in obj_list:
            if o.get() == '':
                pass
            else:
                vals_list.append(o.get())
        for val in vals_list:
            ind = data_titles.index(val)
            index_to_plot_list.append(ind)    
        return index_to_plot_list
 
##############################################################################
#Efficiency or Dark count setup page
##############################################################################

class EDPSetupPage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        label = ttk.Label(self, text="Enter voltage source info and select measurement:", font=LARGE_FONT)
        label.grid(row=1,column=1,padx=20)  

        ttk.Label(self, text="Voltage source slot?:").grid(row=2,column=1)
        VSource_slot = ttk.Entry(self)
        VSource_slot.grid(row=2,column=2)
        
        ttk.Button(self, text="System efficiency measurement", command=lambda: self.confirm_Vsrc(controller, VSource_slot.get(), EfficiencyPage)).grid(row=3,column=1)
        ttk.Button(self, text="Dark counts against bias measurement", command=lambda: self.confirm_Vsrc(controller, VSource_slot.get(), DCRPage)).grid(row=4,column=1)

        ttk.Button(self, text="Go back to instrument setup page", command=lambda: controller.show_frame(StartPage)).grid(row=5,column=1)
        ttk.Button(self, text="Go back to measurement choice page", command=lambda: controller.show_frame(MeasTypePage)).grid(row=6,column=1)

    def confirm_Vsrc(self,controller,VSrc_slot, page_to_go_to):
        if VSrc_slot == '':
            messagebox.showerror('Error', 'No voltage source slot entered!')
            pass
        else:
            controller.SIM_slots["VSource"] = VSrc_slot
            controller.show_frame(page_to_go_to)

##############################################################################
#Efficiency measurement page
##############################################################################

class EfficiencyPage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)        
        ttk.Label(self, text="Start bias?:").grid(row=1,column=1)
        start_bias = ttk.Entry(self)
        start_bias.grid(row=1,column=2)

        ttk.Label(self, text="End bias?:").grid(row=2,column=1)
        end_bias = ttk.Entry(self)
        end_bias.grid(row=2,column=2)

        ttk.Label(self, text="Bias step?:").grid(row=3,column=1)
        bias_step = ttk.Entry(self)
        bias_step.grid(row=3,column=2)

        ttk.Label(self, text="Bias resistor value?:").grid(row=4,column=1)
        bias_r = ttk.Entry(self)
        bias_r.grid(row=4,column=2)

        ttk.Label(self, text="Attenuations? (Seperate with comma if multiple):").grid(row=5,column=1)
        attens= ttk.Entry(self)
        attens.grid(row=5,column=2)

        ttk.Label(self, text="Wavelength? (nm)").grid(row=6,column=1)
        wav= ttk.Entry(self)
        wav.grid(row=6,column=2)

        ttk.Label(self, text="Power at end of fibre? (Watts)").grid(row=7,column=1)
        ip_pwr= ttk.Entry(self)
        ip_pwr.grid(row=7,column=2)

        start_meas_button = ttk.Button(self, text="Start measuring", command=lambda:self.start_meas(controller, start_bias.get(), end_bias.get(), bias_step.get(), bias_r.get(), attens.get(), wav.get(), ip_pwr.get()))
        start_meas_button.grid(row=8,column=1)

        self.working_label = ttk.Label(self, text="No measurement running", foreground='red')
        self.working_label.grid(row=8,column=2)
        
        stop_meas_button = ttk.Button(self, text="Stop measuring", command=lambda:self.stop_meas(controller))
        stop_meas_button.grid(row=9,column=1)

        graph_button = ttk.Button(self, text="Graph", command=lambda: graph_EFF(controller))
        graph_button.grid(row=10,column=1)

        ttk.Button(self, text="Go back to instrument setup page", command=lambda: controller.show_frame(StartPage)).grid(row=11,column=1)
        ttk.Button(self, text="Go back to measurement choice page", command=lambda: controller.show_frame(MeasTypePage)).grid(row=12,column=1)

        #Attenuation calculator
        ttk.Label(self, text="Attenuation calculator", font=LARGE_FONT).grid(row=1,column=3)  

        ttk.Label(self, text="Laser rep rate? (1 for CW):").grid(row=2,column=3)
        laser_rr = ttk.Entry(self)
        laser_rr.grid(row=3,column=3)

        calc_atten_button = ttk.Button(self, text="Calculate attenuation", command=lambda: self.calculate_atten(laser_rr.get(), wav.get(), ip_pwr.get()))
        calc_atten_button.grid(row=4, column=3)
        
        ttk.Label(self, text="Attenuation for 0.1 photons/s (or 1000000 per s for CW):").grid(row=5, column=3)
        self.atten_value_label = ttk.Label(self, text='')
        self.atten_value_label.grid(row=6, column=3)


    def start_meas(self, controller, start_bias, stop_bias, bias_step, bias_r, attens, wav, ip_pwr):
        if start_bias == '':
            messagebox.showerror('Error', 'Enter a valid start bias value')
        elif stop_bias == '':
            messagebox.showerror('Error', 'Enter a valid stop bias value')
        elif bias_step == '':
            messagebox.showerror('Error', 'Enter a valid bias step value')
        elif bias_r == '':
            messagebox.showerror('Error', 'Enter a valid bias resistor value')
        elif attens == '':
            messagebox.showerror('Error', 'Enter a valid attenuation value')
        elif wav == '':
            messagebox.showerror('Error', 'Enter a valid wavelength value')
        elif ip_pwr == '':
            messagebox.showerror('Error', 'Enter a valid input power value')
        else:
            controller.EFF_filename = os.path.dirname(os.path.abspath(__file__))+"\\Data\\"+time.ctime().replace(" ", "_").replace(":","_")+"EFF.txt"
            self.first_atten = True
            self.biases = np.arange(float(start_bias), float(stop_bias)+float(bias_step), float(bias_step)) 
            self.bias_r = float(bias_r)
            self.attens = attens.split(',')
            self.wav = int(wav)
            self.ip_pwr = float(ip_pwr)
        #open pulse counter    
            controller.PCounter = controller.rm.open_resource(controller.instr_address_dict['pulse_c_address'])
        #setup pulse counter
            controller.PCounter.write(':INP1:COUP DC;IMP 50 OHM')
            controller.PCounter.write('SENS:TOT:ARM:STOP:TIM 1')
        #open sim900
            controller.sim900 = SIM900(controller.instr_address_dict['sim900_address'])
        #open attenuator
            if controller.manual_atten == False:
                controller.Op_Attn_1 = controller.rm.open_resource(controller.instr_address_dict["opat1_address"])
                if controller.instr_address_dict["opat2_address"] != '':
                    controller.Op_Attn_2 = controller.rm.open_resource(controller.instr_address_dict["opat2_address"])

            self.working_label['text']="Measurement running!"
            self.working_label['foreground']='green'
            self.setup_measurement(controller)

    def calc_photon_flux(self, atten, wavelength, input_pwr):
        h = 6.626070040e-34
        c = 2.99792458e8
        out_pwr = (float(input_pwr))*(10**(-float(atten)/10)) 
        E_per_photon = h*(c/(int(wavelength)*1e-9)) #convert wlength to m 
        photon_flux = out_pwr/E_per_photon
        return photon_flux

    def calc_efficiency(self, P_counts,D_counts, photon_flux):
        eff = ((P_counts-D_counts)/photon_flux)*100
        return eff

    def setup_measurement(self, controller):
        if self.first_atten == True:   #Sets up the counter for attenuations
            self.atten_id = 0
            self.first_atten = False
        if self.atten_id >= len(self.attens):
            self.working_label['text']="No measurement running"
            self.working_label['foreground']='red'
            controller.measurement_after_id = None
            if controller.manual_atten == False:
                controller.Op_Attn_1.write(':OUTP:STAT OFF')
        else:
            self.atten = int(self.attens[self.atten_id])
            self.photon_flux = self.calc_photon_flux(self.atten, self.wav, self.ip_pwr)
            with open(controller.EFF_filename, 'a+') as file_handle:
                writer_csv =  csv.writer(file_handle, delimiter=',')
                writer_csv.writerow((['ATTENUATION', self.atten, self.photon_flux ]))
            if controller.manual_atten == False:    #If two attenuators needed use both
                if controller.instr_address_dict["opat2_address"] != '':
                    controller.Op_Attn_1.write(':INP:ATT '+ str(self.atten/2) + ' dB')
                    controller.Op_Attn_2.write(':INP:ATT '+ str(self.atten/2) + ' dB')
                    controller.Op_Attn_2.write(':OUTP:STAT ON')
                else:    #else use one
                    controller.Op_Attn_1.write(':INP:ATT '+ str(self.atten) + ' dB')
            self.get_EFF_data(controller)
        
    def get_EFF_data(self, controller):
        if controller.measurement_after_id == None:    #Sets up the counter for bias points
            self.bias_id = 0
        #SET BIAS
        controller.sim900.write(controller.SIM_slots['VSource'], 'VOLT %.3f'%self.biases[self.bias_id])
        controller.sim900.write(controller.SIM_slots['VSource'],'OPON')
        #TAKE DATA
        #DC
        self.counts_cont=[]
        if controller.manual_atten == False:
            controller.Op_Attn_1.write(':OUTP:STAT OFF')
        else:
            messagebox.showinfo('Block input', 'Block the light into the fibre')
        while len(self.counts_cont) < 5:
            controller.PCounter.write('SENS:TOT:ARM:STOP:TIM 1')
            self.counts_cont.append(float(controller.PCounter.query("READ?")))
        DC_val = sum(self.counts_cont)/5
        
        #PC
        if controller.manual_atten == False:
            controller.Op_Attn_1.write(':OUTP:STAT ON')
        else:
            messagebox.showinfo('Unblock input', 'Allow the light into the fibre')
        self.counts_cont = []
        while len(self.counts_cont) < 5:
            controller.PCounter.write('SENS:TOT:ARM:STOP:TIM 1')
            self.counts_cont.append(float(controller.PCounter.query("READ?")))
        PC_val = sum(self.counts_cont)/5
        eff = self.calc_efficiency(PC_val, DC_val, self.photon_flux)

        data_to_write = ([self.biases[self.bias_id], DC_val, PC_val, eff])
        #WRITE DATA
        with open(controller.EFF_filename, 'a+') as file_handle:
            writer_csv =  csv.writer(file_handle, delimiter=',')
            writer_csv.writerow(data_to_write)
        self.bias_id += 1
        if self.bias_id < len(self.biases):    #check doing all points here
            controller.measurement_after_id = app.after(1500, self.get_EFF_data, controller)    #wait 1s, go again.
        elif self.bias_id == len(self.biases):
            controller.sim900.write(controller.SIM_slots['VSource'],'OPOF')    #turn bias off before changing attenuations
            self.atten_id += 1
            controller.measurement_after_id = None
            self.setup_measurement(controller)

    def stop_meas(self, controller):
        if controller.measurement_after_id != None:
            app.after_cancel(controller.measurement_after_id)
            controller.measurement_after_id = None
        self.working_label['text']="No measurement running"
        self.working_label['foreground']='red'

    def calculate_atten(self, laser_r, wav, power):
        h = 6.626070040e-34
        c = 2.99792458e8
        if laser_r == '':
            messagebox.showerror('Error', 'Enter a valid laser rep rate')
        elif wav == '':
            messagebox.showerror('Error', 'Enter a valid wavelength')
        elif power == '':
            messagebox.showerror('Error', 'Enter a valid power')
        else:
            ppp = []
            laser_rr=float(laser_r)
            energy_per_photon = h*(c/(float(wav)/1e9))
            if laser_rr == 1:    #For CW
                ideal_num = 1000000
            else:    #For pulsed
                ideal_num = 0.1
            for i in range(0,180):    #Goes through 0to180dB attenuations and calculates photons per pulse for each
                ph_p_pul = (float(power)*10**(-(float(i)/10))/energy_per_photon)*(1/laser_rr)
                ppp.append(ph_p_pul)
            nearest = min(ppp, key=lambda x:abs(x-ideal_num))    #Finds nearest value to ideal value
            self.atten_value_label['text'] = str(ppp.index(nearest))+'dB'

##############################################################################
#DCR measurement page
##############################################################################

class DCRPage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        ttk.Label(self, text="Start bias?:").grid(row=1,column=1)
        start_bias = ttk.Entry(self)
        start_bias.grid(row=1,column=2)

        ttk.Label(self, text="End bias?:").grid(row=2,column=1)
        end_bias = ttk.Entry(self)
        end_bias.grid(row=2,column=2)

        ttk.Label(self, text="Bias step?:").grid(row=3,column=1)
        bias_step = ttk.Entry(self)
        bias_step.grid(row=3,column=2)

        ttk.Label(self, text="Bias resistor value?:").grid(row=4,column=1)
        bias_r = ttk.Entry(self)
        bias_r.grid(row=4,column=2)

        start_meas_button = ttk.Button(self, text="Start measuring", command=lambda:self.start_meas(controller, start_bias.get(), end_bias.get(), bias_step.get(), bias_r.get()))
        start_meas_button.grid(row=5,column=1)

        self.working_label = ttk.Label(self, text="No measurement running", foreground='red')
        self.working_label.grid(row=5,column=2)
        
        stop_meas_button = ttk.Button(self, text="Stop measuring", command=lambda:self.stop_meas(controller))
        stop_meas_button.grid(row=6,column=1)

        graph_button = ttk.Button(self, text="Graph", command=lambda: extract_data(controller, 'DCR'))
        graph_button.grid(row=7,column=1)

        ttk.Button(self, text="Go back to instrument setup page", command=lambda: controller.show_frame(StartPage)).grid(row=8,column=1)
        ttk.Button(self, text="Go back to measurement choice page", command=lambda: controller.show_frame(MeasTypePage)).grid(row=9,column=1)
        
    def start_meas(self, controller, start_bias, stop_bias, bias_step, bias_r):
        controller.Filename = os.path.dirname(os.path.abspath(__file__))+"\\Data\\"+time.ctime().replace(" ", "_").replace(":","_")+"_DCR.txt"
        with open (controller.Filename, 'a+') as DCR_file:
            writer_csv = csv.writer(DCR_file, delimiter=',')
            writer_csv.writerow(['Time(s)', 'VSrc(V)', 'ISrc(A)', 'Counts(CPS)'])
        self.biases = np.arange(float(start_bias), float(stop_bias)+float(bias_step), float(bias_step)) 
        self.bias_r = bias_r
        controller.PCounter = controller.rm.open_resource(controller.instr_address_dict['pulse_c_address'])
        #setup pulse counter
        controller.PCounter.write(':INP1:COUP DC;IMP 50 OHM')
        controller.PCounter.write('SENS:TOT:ARM:STOP:TIM 1')
        #open sim900
        controller.sim900 = SIM900(controller.instr_address_dict['sim900_address'])
        self.working_label['text']="Measurement running!"
        self.working_label['foreground']='green'
        self.get_DCR_data(controller)
        
    def get_DCR_data(self, controller):
        if controller.measurement_after_id == None:
            self.start_time_meas = time.time()
            self.bias_id = 0
        #SET BIAS
        controller.sim900.write(controller.SIM_slots['VSource'], 'VOLT %.3f'%self.biases[self.bias_id])
        controller.sim900.write(controller.SIM_slots['VSource'],'OPON')
        #TAKE DATA
        data_to_write = [str(time.time()-self.start_time_meas)]#time
        data_to_write.append(str(self.biases[self.bias_id]).strip()) #voltage
        I_src = self.biases[self.bias_id]/float(self.bias_r) #work out the current from the bias r
        data_to_write.append(str(I_src).strip())
        data_to_write.append(float(controller.PCounter.query('READ?')))
        #WRITE DATA
        with open(controller.Filename, 'a+') as file_handle:
            writer_csv =  csv.writer(file_handle, delimiter=',')
            writer_csv.writerow(data_to_write)
        self.bias_id += 1
        if self.bias_id < len(self.biases):#check doing all points here
            controller.measurement_after_id = app.after(1500, self.get_DCR_data, controller) #wait 1.5s, go again.
        else:
            self.working_label['text']="No measurement running"
            self.working_label['foreground']='red'
            controller.measurement_after_id = None

    def stop_meas(self, controller):
        if controller.measurement_after_id != None:
            app.after_cancel(controller.measurement_after_id)
            controller.measurement_after_id = None
        self.working_label['text']="No measurement running"
        self.working_label['foreground']='red'

##############################################################################
#Plot existing data file page
##############################################################################

class PlotExistingFilePage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.generic_filename = ''
        label = ttk.Label(self, text="Load a file and select the plot type:", font=LARGE_FONT)
        label.grid(row=1,column=1,padx=20)

        load_file_button = ttk.Button(self, text="Select file", command=self.load_file)
        load_file_button.grid(row=2,column=1)

        plot_eff_b = ttk.Button(self, text='Plot efficiency file', command=lambda: self.plot_type_handler(controller,'EFF'))
        plot_eff_b.grid(row=3,column=1)

        plot_DCR_b = ttk.Button(self, text='Plot dark count against bias file', command=lambda: self.plot_type_handler(controller,'DCR'))
        plot_DCR_b.grid(row=4,column=1)

        plot_VvT_b = ttk.Button(self, text='Plot values vs time file', command=lambda: self.plot_type_handler(controller,'VvT'))
        plot_VvT_b.grid(row=5,column=1)

    def load_file(self):
        self.generic_filename = askopenfilename(initialdir="Z:\\", title="Choose a file")
    
    def plot_type_handler(self,controller, plt_type):
        if self.generic_filename == '':
            messagebox.showerror('Error', 'No file loaded!')
        else:
            if plt_type == 'EFF':
                controller.EFF_filename = self.generic_filename
                graph_EFF(controller)

            elif plt_type == 'DCR':
                controller.Filename = self.generic_filename
                extract_data(controller, plt_type)

            elif plt_type == 'VvT':
                controller.Filename = self.generic_filename
                extract_data(controller, plt_type)

##############################################################################
#R-T Pages
##############################################################################

class RTPage(ttk.Frame):
    def __init__(self, parent, controller):
        Frame.__init__(self, parent)

        label = ttk.Label(self, text="RT measurement: Ensure V-src is voltmeter input 1 and V-dev is input 2", font=LARGE_FONT)
        label.grid(row=1,column=1,padx=20)

        ttk.Label(self, text="Bias resistor value?:").grid(row=2,column=1)
        bias_r = ttk.Entry(self)
        bias_r.grid(row=3,column=1)

        ttk.Label(self, text="Bias point to run measurement at?:").grid(row=4,column=1)
        bias_point=ttk.Entry(self)
        bias_point.grid(row=5,column=1)

        start_meas_button = ttk.Button(self, text="Start measuring", command=lambda:self.start_meas(controller, bias_r.get(), bias_point.get()))
        start_meas_button.grid(row=6,column=1)

        self.working_label = ttk.Label(self, text="No measurement running", foreground='red')
        self.working_label.grid(row=7,column=1)
        
        stop_meas_button = ttk.Button(self, text="Stop measuring", command=lambda:self.stop_meas(controller))
        stop_meas_button.grid(row=8,column=1)

        graph_button = ttk.Button(self, text="Graph", command=lambda: extract_data(controller, 'RT'))
        graph_button.grid(row=9,column=1)

        ttk.Button(self, text="Go back to instrument setup page", command=lambda: controller.show_frame(StartPage)).grid(row=10,column=1)
        ttk.Button(self, text="Go back to measurement choice page", command=lambda: controller.show_frame(MeasTypePage)).grid(row=11,column=1)

    def start_meas(self, controller, bias_r, bias_point):
        controller.Filename = os.path.dirname(os.path.abspath(__file__))+"\\Data\\"+time.ctime().replace(" ", "_").replace(":","_")+"_RT.txt"
        with open (controller.Filename, 'a+') as RT_file:
            writer_csv = csv.writer(RT_file, delimiter=',')
            writer_csv.writerow(['Time(s)', 'T1(K)', 'T2(K)', 'T3(K)', 'VSrc(V)', 'VDev(V)', 'RDev'])
        self.bias_r = float(bias_r)
        #open sim900 and set the bias point
        controller.sim900 = SIM900(controller.instr_address_dict['sim900_address'])
        controller.sim900.write(controller.SIM_slots['VSource'], 'VOLT '+bias_point)
        controller.sim900.write(controller.SIM_slots['VSource'],'OPON')
        self.working_label['text']="Measurement running!"
        self.working_label['foreground']='green'
        self.get_RT_data(controller)

    def get_RT_data(self, controller):
        if controller.measurement_after_id == None:
            self.start_time_meas = time.time()
        #TAKE DATA
        data_to_write = [str(time.time()-self.start_time_meas)]#time
        t1 = str(controller.sim900.ask(controller.SIM_slots['ThermSlot'],'TVAL? 1')).strip()
        t2 = str(controller.sim900.ask(controller.SIM_slots['ThermSlot'],'TVAL? 2')).strip()
        t3 = str(controller.sim900.ask(controller.SIM_slots['ThermSlot'],'TVAL? 3')).strip()
        Vsrc=float(controller.sim900.ask(controller.SIM_slots['VMeter'],'VOLT? 1,1').strip().split(' ')[-1])
        Vdev=float(controller.sim900.ask(controller.SIM_slots['VMeter'],'VOLT? 2,1').strip())
        R = Vdev/((Vsrc-Vdev)/self.bias_r)
        data_to_write+=[t1,t2,t3,Vsrc,Vdev,R]
        #WRITE DATA
        with open(controller.Filename, 'a+') as file_handle:
            writer_csv =  csv.writer(file_handle, delimiter=',')
            writer_csv.writerow(data_to_write)

        controller.measurement_after_id = app.after(1000, self.get_RT_data, controller) #wait 1s, go again.
        
    def stop_meas(self, controller):
        if controller.measurement_after_id != None:
            app.after_cancel(controller.measurement_after_id)
            controller.measurement_after_id = None
        self.working_label['text']="No measurement running"
        self.working_label['foreground']='red'
        controller.sim900.write(controller.SIM_slots['VSource'],'OPOF')

##############################################################################
#Functions
##############################################################################

def extract_data(controller, plt_type):
    if controller.measurement_after_id != None:
        messagebox.showerror('Error', 'Measurement still running')
    else:
        controller.plot_arrays_dict={}
        with open(controller.Filename) as csv_file:
            read_csv = csv.reader(csv_file, delimiter=',')
            for index, row in enumerate(read_csv):
                if len(row)>0:
                    if index==0:
                        controller.data_titles = row
                        number_cols = len(row)
                        for i in range(number_cols):
                            controller.plot_col_dict[i]=[]
                    else:
                        for i in range(number_cols):
                            controller.plot_col_dict[i].append(row[i])
        for i in range(number_cols):
            controller.plot_arrays_dict[i]=np.asarray(controller.plot_col_dict[i], dtype='float')
        controller.plot_type = plt_type
        controller.show_frame(DisplayGraphPage)


def graph_EFF(controller):
    if controller.measurement_after_id != None:
        messagebox.showerror('Error', 'Measurement still running')
    else:
        controller.plot_arrays_dict={}
        controller.eff_dict = {}
        bias_list=[]
        with open(controller.EFF_filename) as csv_file:
            read_csv = csv.reader(csv_file, delimiter=',')
            for index, row in enumerate(read_csv):
                if len(row)>0:
                    if index == 0:#first time around
                        atten=row[1]
                        eff_list = []#empty eff container
                    elif row[0] =='ATTENUATION':#subsequent data sets
                        controller.eff_dict[atten] = np.asarray(eff_list, dtype='float')#save off the data
                        atten = row[1]#new atten
                        eff_list=[]#reset eff container
                    else:
                        eff_list.append(row[3])
                        if row[0] not in bias_list:#only want one list of biases as the same for each atten
                            bias_list.append(row[0])
            #Last one (no 'ATTENUTION' flag
        controller.eff_dict[atten] = np.asarray(eff_list, dtype='float')
        controller.bias_arr = np.asarray(bias_list, dtype='float')*10#uA
        controller.plot_type = 'EFF'
        controller.show_frame(DisplayGraphPage)

##############################################################################
#Main code
##############################################################################

app = DataGatheringapp()
app.geometry("800x400")
app.mainloop()

##############################################################################
#Error logging
##############################################################################

#logger=exception_logger(".\\ErrorLog\\ErrorLog.log")


