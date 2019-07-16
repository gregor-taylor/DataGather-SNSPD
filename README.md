Tkinter app for taking data from various apparatus. All common measurements for SNSPD characterisation are covered.</br>

Start page:</br>
- Add all of the instruments that you want to use for your measurement; SIM900, ThorlabsPMT100 power meter, HP/Keysight programmable optical attenuators,
Agilent pulse counter - more to be added.</br>
- Refresh button will refresh currently connected instrument list.</br>
- Existing file button will allow loading of data previously taken with this program to plot it in here. </br>

Measurement type page:</br>
- Currently supported types are RT measurement (not tested), generic values (i.e power and counts) against time or Efficiency/DCR/PCR.</br>

Values against time page:</br>
- Takes values taken from any instruments against time.</br> 
- Insert values for Vsource/Vmeter/etc slots in the SIM900 as required.</br> 
- Takes you to working page where the measurement can be started, stopped and (once stopped) plotted.</br>

Efficiency or DCR measurement:</br>
- Used to take DCR/PCR vs bias measurements or full system detection efficiency measurements.</br>
- Insert VSource slot in SIM900.</br>
- Define the bias range required, bias resistor used, attenuation(s) and optical power and wavelength at the input to the system.</br>
- An attenuation calculator is provided to assist with choosing attenuations for a given photons/pulse. Just input the wavelength/power/ph per pulse required. </br> 
- DCR/PCR will then just sweep the bias as you define and take counts from the counter. Can then be plotted.</br>
- Efficiency measurements work by setting up a attenuation (user input), taking a bias point, turning the light source OFF by blocking the attenuator,
taking 5 DCR points, turning the laser ON and taking 5 PCR points. It then averages these so it has 1 DCR and 1 PCR point for that bias and attenuation.
Bias is then increased by the step size defined and the mesurement is repeated. Once all the points for the bias range are gathered the efficiency vs
 bias plot can be obtained by PCR-DCR/Input photon flux. If more than one attenuation is required then the program will just set a different attenuation and 
repeat the measurement. </br>
- An option for manual blocking/attenuation is implemented. Useful when no programmable attenuators are available. When no attenuators are input to the instrument setup page 
it will default to this mode. In this mode the program will prompt you to block/unblock the input as required.</br> 

Plot page:</br>
- Plots the data gathered in each measurement or previously gathered.</br>
- If you move the file then you will have to reload it.</br>
- Designed more for a quick look rather than detailed/publication ready plots.</br>

RT Page:</br>
- NOT TESTED</br>
- Sets a bias point, and then takes resistance measurements as the device cools or warms up.</br>
- Then can plot resistance against temperature.</br>
