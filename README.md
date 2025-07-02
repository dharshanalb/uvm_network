**UVM_NETWORK**
uvm network is a currently in ALPHA version 

uvm_network simplifies connecting various uvm components such as drivers,
monitors, scoborads etc... 

First in your uvm envrionment/agents's build phase instantiate the network
then Put this network into a configDB so this is accesible in your tb  
`def build_phase(self):
    self.network    = uvm_network("network", self)
    ConfigDB().set(None, "*", "NETWORK", self.network)`
 
then add paths between uvm components. 
 add_path(source , sink) 
 source => where the data is generated 
 sink   => where the data is destined to end up at 
`def connect_phase(self):
        self.network.add_path("sequencer", "driver"     )
        self.network.add_path("cmd_mon"  , "scoreboard" )
        self.network.add_path("res_mon"  , "scoreboard" )`

then in a source uvm component 
call up configDB to get access to the network 
self.network = ConfigDB().get(None, "", "NETWORK")

When you want to send data to a sink then do this 

`self.network.put_noack("cmd_mon", "scoreboard", data)`
"

`await self.network.put_ack("sequencer","driver", data) `


