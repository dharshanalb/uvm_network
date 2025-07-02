"""
uvm network where you can create network paths and send packets around
"""
import cocotb
from cocotb.queue import Queue
from pyuvm import uvm_object, uvm_component
from uvm_packet import TxState, TxMode, uvm_packet
from icecream import ic
from parameters_validation import validate_parameters,strongly_typed, non_blank

class uvm_network(uvm_component):
    """
    class definition of uvm network
    """
    @validate_parameters
    def __init__(
        self, 
        name   : strongly_typed(str),  # type: ignore
        parent : strongly_typed(uvm_component)   # type: ignore
    ):
        super().__init__(name, parent)
        self.name         = name
        self.parent       = parent
        self.path_list    = []
        self.queue_dict   = {}
        self.ack_db       = {}
        self.flush_db     = []

        ##########################        
        self.err_msg_path_does_not_exist = "[ERR-1] path does not exist in this network"
        self.err_msg_path_duplication    = "[ERR-2] path already exists, path name should be unique"
        self.err_msg_no_paths_with_source= "[ERR-3] there are no paths with this source"
        self.err_msg_no_paths_with_sink  = "[ERR-4] there are no paths with this sink"
        self.err_msg_no_available_paths  = "[ERR-5] There are no available paths"
        self.err_msg_invalid_ack_status  = "[ERR-6] invalid ack status"
        self.err_msg_invalid_ack_process = "[ERR-7] invalid/null ack processing function"

    @validate_parameters
    def log_error(
        self, 
        func_name : non_blank(str), # type: ignore
        err_msg   : non_blank(str), # type: ignore 
        var_dict  : strongly_typed(dict), # type: ignore 
    ):
        err_str = f"{func_name} :: {err_msg}"
        ic.configureOutput(prefix="")
        var_str = ic.format(var_dict)

        self.logger.error(f"{err_str} :: {var_str}")


    @validate_parameters
    def set_path(
        self, 
        source:non_blank(str), # type: ignore
        sink  :non_blank(str)  # type: ignore
    ) -> tuple: 
        """
            return a tuple made from source & sink
        """
        path = (source, sink)

        return path

    @validate_parameters
    def valid_path(
        self,
        source :non_blank(str),              # type: ignore
        sink   :non_blank(str),              # type: ignore
        err_en :strongly_typed(bool) = True  # type: ignore
    ) -> bool:
        """
            check if the path tuple is already in self.path_list.
            uvm error can be enabled/disabled optionally
        """
        path          = self.set_path(source, sink)
        path_list_tmp = self.get_path_list()
                
        if path in path_list_tmp:
            return True 
        else:
            if err_en: 
                self.log_error(self.valid_path.__name__, self.err_msg_path_does_not_exist, locals())
            return False 
        
    @validate_parameters
    def add_path(
        self, 
        source :non_blank(str), # type: ignore
        sink   :non_blank(str), # type: ignore
    )-> bool:
        """
            add a new path to the network
        """        
        path   = self.set_path(source, sink)
        
        #path is not already setup, so ok to add to the network
        if not(self.valid_path(source, sink, err_en=False)):
            self.path_list.append(path)
            self.queue_dict[path] = Queue(maxsize = 0) #always infinite queue
            self.ack_db.setdefault(path,{}) #init ack db
            return True
        else:
            self.log_error(self.add_path.__name__, self.err_msg_path_duplication, locals())
            return False
        
    @validate_parameters
    def get_paths_from_source(
        self, 
        source :non_blank(str), # type: ignore
    ) -> list[tuple]:
        """
            get all the paths which have the same source
        
        Args:
            source (str): provide the name of the source 

        Returns:
            list[tuple]: return a list of path tuples
        """
        path_list_tmp = self.get_path_list()
        path_list_res = [] 
        
        for path in path_list_tmp:
            (cmp_source, _) = path
            if cmp_source == source:
                path_list_res.append(path)

        if len(path_list_res) == 0:
            self.log_error(self.get_paths_from_source.__name__, self.err_msg_no_paths_with_source, locals())

        return path_list_res

    @validate_parameters
    def get_paths_from_sink(
        self, 
        sink :non_blank(str), # type: ignore
    ) -> list[tuple]:
        """
            get all the paths which have the same sink
        """
        path_list_tmp = self.get_path_list()
        path_list_res = []

        for path in path_list_tmp:
            (_, cmp_sink) = path
            if cmp_sink == sink:
                path_list_res.append(path)
        
        if len(path_list_res) == 0:
            self.log_error(self.get_paths_from_sink.__name__, self.err_msg_no_paths_with_sink, locals())

        return path_list_res

    def get_path_list(self) -> list[tuple]:
        """
            return the list of paths in the network
        """
        return self.path_list

    @validate_parameters
    async def put(
        self,
        source : non_blank(str),        # type: ignore
        sink   : non_blank(str),        # type: ignore
        mode   : strongly_typed(TxMode),# type: ignore       
        data,                           # very weak type!        
    ) -> uvm_packet:
        """
            put the data to the network path
        """
        req_pkt = uvm_packet("req_pkt")

        #setup the path tuple
        path = self.set_path(source, sink)

        #check if path is already setup
        if self.valid_path(source, sink):
            #create the req packet
            req_pkt.set_all(
                source,
                sink, 
                self.qsize(source, sink)+1, 
                TxState.IDLE, 
                mode, 
                data, 
                None
            )
            #we have started sending request
            req_pkt.set_state_started() 

            if req_pkt.is_ack_required():
                #create special ack path for this request
                self.ack_db[path][req_pkt.get_pkt_id()] = Queue(maxsize=1)
                #send out the request packet
                self.queue_dict[path].put_nowait(req_pkt)            
                #get back the ack
                return await self.ack_db[path][req_pkt.get_pkt_id()].get() 

            else:
                self.queue_dict[path].put_nowait(req_pkt)
                req_pkt.set_state_done() #no ack required
                return req_pkt
        else:
            self.log_error(self.put.__name__, self.err_msg_path_does_not_exist, locals())
            return None

    @validate_parameters
    async def put_noack(
        self, 
        source : non_blank(str),        # type: ignore
        sink   : non_blank(str),        # type: ignore
        data,                           # very weak type!
    ) -> bool:
        """
        perform a put where no ack is required
        """
        pkt = await self.put(source, sink, TxMode.NOACK, data)

        return pkt.is_state_done()

    @validate_parameters
    async def put_ack(
        self, 
        source : non_blank(str),              # type: ignore
        sink   : non_blank(str),              # type: ignore
        data,                                 # very weak type!
        err_en : strongly_typed(bool)= True   # type: ignore
    ) -> bool:
        """
        perform a put where ack is required
        """
        pkt = await self.put(source, sink, TxMode.ACK, data)

        if pkt.is_state_done():
            return True
        else:
            if err_en:
                self.log_error(self.put_ack.__name__, self.err_msg_invalid_ack_status, locals())
            return False

    @validate_parameters
    async def put_ack_data(
        self, 
        source : non_blank(str),            # type: ignore
        sink   : non_blank(str),            # type: ignore
        data,                               # very weak type!
        err_en : strongly_typed(bool)= True # type: ignore
    ) -> uvm_object:
        """
        perform a put with data is required, and data is returned back
        """
        pkt      = await self.put(source, sink, data, TxMode.ACK_WITH_DATA)

        if pkt.is_state_done():
            return pkt.get_ack_obj()
        else:
            if err_en:
                self.log_error(self.put_ack_data.__name__, self.err_msg_invalid_ack_status, locals())
                return None 
            else:
                return pkt.get_ack_obj() #return the ack object regardless of error

    @validate_parameters
    async def get(
        self, 
        source : non_blank(str), # type: ignore
        sink   : non_blank(str), # type: ignore
        proc_func = None,        # a function here
        *arg,                    # very weak type!
        **kwargs                 # very weak type!
    ) -> uvm_object:
        """
            get data from the  network path
            output => req_object
        """                   
        #setup the path tuple 
        path    = self.set_path(source, sink)
        
        #check if the path is already setup 
        if self.valid_path(source, sink):
            #pull in the uvm packet
            req_pkt = await self.queue_dict[path].get()
            req_obj = req_pkt.get_req_obj() 
        
            #no ack required
            if req_pkt.is_ack_required():
                if (proc_func == None):
                    self.get(self.put_ack_data.__name__, self.err_msg_invalid_ack_process, locals())
                else:
                    #process the request packet
                    ack_pkt  = await proc_func(req_pkt, *arg, **kwargs)
                    self.ack_db[path][ack_pkt.get_pkt_id()].put_nowait(ack_pkt) #send ack
            
            return req_obj
        else:            
            return None

    @validate_parameters          
    async def broadcast_noack(
        self, 
        source : non_blank(str), # type: ignore
        data                     # very weak type!
    ) -> bool:
        """
            broadcast the data to all the sinks connected the source, paths set to noack
        """
        path_list_tmp = self.get_paths_from_source(source)
        task_list = []

        if len(path_list_tmp) <= 0: 
            return False
       
        #put concurrently
        
        for path in path_list_tmp:  
            (source, sink) = path          
            put_task = cocotb.start_soon(self.put_noack(source, sink, data))
            task_list.append(put_task) 
        
        global_status = True 
        for task in task_list:
            task_status   = await task
            global_status = global_status and task_status
       
        return global_status

    @validate_parameters    
    async def broadcast_ack(
        self, 
        source : non_blank(str), # type: ignore
        data                     # very weak type!    
    ) -> bool:
        """
            broadcast the data to all the sinks connected the source, paths set to ack
        """
        path_list_tmp = self.get_paths_from_source(source)
        task_list = []
        
        if len(path_list_tmp) <= 0:
            return False

        for path in path_list_tmp:
            (source, sink) = path
            put_task       = cocotb.start_soon(self.put_ack(source, sink, data))
            task_list.append(put_task) 

        global_status = True 
        for task in task_list:
            task_status   = await task
            global_status = global_status and task_status

        return global_status
    
    @validate_parameters    
    async def broadcast_ack_data(
        self, 
        source : non_blank(str), # type: ignore
        data                     # very weak type!
    ) -> list[(str,uvm_object)]:
        """broadcast the data to all the sinks connected the source, paths set to ack with data

        Returns:
            list of tuple, each tuple will contain the name of the sink that sent the ack data and the ack data
        """
        
        path_list_tmp = self.get_paths_from_source(source)
        task_list     = []
        data_list     = []

        if len(path_list_tmp) <= 0:
            return False
        
        #start sending to all the sinks concurrenlty
        for path in path_list_tmp:
            (source, sink) = path
            put_task       = cocotb.start_soon(self.put_ack_data(source, sink, data))
            task_list.append(put_task) 

        #wait for ack and return a list of tuples (sink_name, ack_object)
        for task in task_list:
            ack_pkt = await task 
            data_list.append((self.get_sink(ack_pkt.get_path()), ack_pkt.get_ack_obj()))

        return data_list

    @validate_parameters    
    def empty(
        self, 
        source : non_blank(str), # type: ignore
        sink   : non_blank(str), # type: ignore
    ) -> bool:
        """
            check if network path is empty
        """
        path = self.set_path(source, sink)

        if self.valid_path(source, sink):
            return self.queue_dict[path].empty()
        else:
            return None

    @validate_parameters
    def qsize(
        self, 
        source : non_blank(str), # type: ignore
        sink   : non_blank(str), # type: ignore
    ) -> int:
        """
            get the qsize of network path
        """
        path  = self.set_path(source, sink)
        
        if self.valid_path(source, sink):
            return self.queue_dict[path].qsize()
        else:
            return None

