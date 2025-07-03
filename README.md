# UVM_NETWORK

## Introduction
**uvm network is a currently in ALPHA version**

uvm_network simplifies connecting various uvm components such as drivers,
monitors, scoborads etc... 

### Step 1
in your uvm envrionment/agents's build phase instantiate the uvm_network
then Put this network into a configDB so this is globally accesible  
<br>
uvm_network object must be instatiated with a descriptive name, and the parent object. (same as uvm_component)
```
def build_phase(self):
    self.network    = uvm_network("network", self)
    ConfigDB().set(None, "*", "NETWORK", self.network)
```
 
### Step 2 
then add paths between uvm components in the connect phase
```
add_path(<source> , <destination>)
``` 
***source*** : where the data is generated, must be a unique string <br>
***destination***   : where the data is destined to end up at, must be a unique string 
```
def connect_phase(self):
        self.network.add_path("sequencer", "driver"    )
        self.network.add_path("cmd_mon"  , "scoreboard")
        self.network.add_path("res_mon"  , "scoreboard")
```
### Step 3
then in a source uvm component (i.e the component which generates the data) 
call up configDB to get access to the network 
```
self.network = ConfigDB().get(None, "", "NETWORK")
```
When you want to send data to a destination then you need to use a put method with source, destination and transmit data. Python uses duck typing so "data" can be any object or variable. 

****put_noack****<br>
Simplest put method. Put the data with source & destination. No need wait, this is a non-blocking function.
```
self.network.put_noack("cmd_mon", "scoreboard", data)
```
****put_ack****<br>
slightly more complicated. Put the data with source & destination and wait for the ack from destination. 
```
await self.network.put_ack("sequencer","driver", data)
```
****put_ack_data****<br>
Even more  complicated. Put the data with source & destination and wait for the ack and return data from the destination. 
```
ack_data = await self.network.put_ack_data("sequencer","driver", data)
```
### Step 4
then in a destination uvm component (i.e the component which data comes to) call up configDB to get access to the network 
```
self.network = ConfigDB().get(None, "", "NETWORK")
```
When you want to receive data from a source then you need to use get method with source, destination & callback function (optional). Python uses duck typing so "data" can be any object or variable. 

* if the source does not expect ack back then you just need to wait  to received data. 
```
var = await self.network.get("cmd_mon","scoreboard") 
```

* if the source does expect ack data back then you need to define a callback function to process the ack data. This callback should take uvm_packet object as input. 
```
async def proc_driver(self, pkt :uvm_packet) -> uvm_packet:
    req_obj = pkt.get_req_obj()
    <Do some processing>
    pkt.set_state_done() <set to done for ack>
    return pkt
```
* provide this callback to the get method
```
var = await self.network.get("sequencer", "driver", proc_driver)
```

**See /basic_test folder for a simple implementation**<br>
compare with this with https://github.com/pyuvm/pyuvm/blob/master/examples/TinyALU/testbench.py. 
Do you think uvm_network simplifies pyuvm test bench ? 
