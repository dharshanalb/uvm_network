"""uvm packet"""
from enum import Enum
from pyuvm import uvm_object
from parameters_validation import validate_parameters,strongly_typed, non_blank

class TxState(Enum):
    """transaction state of uvm_packet"""
    IDLE        = 0
    STARTED     = 1
    DONE        = 2
    ABORT       = 3

class TxMode(Enum):
    """transaction mode of uvm_packet"""
    NOACK         = 0
    ACK           = 1
    ACK_WITH_DATA = 2

class uvm_packet(uvm_object):
    """uvm packet class"""
    @validate_parameters
    def __init__(
        self,
        name : strongly_typed(str) #type: ignore
    ):
        super().__init__(name)
        self.source  = ""
        self.sink    = ""
        self.path    = ()
        self.pkt_id  = -1
        self.state   = TxState.IDLE
        self.mode    = TxMode.NOACK
        self.req_obj = uvm_object("req_obj")
        self.ack_obj = uvm_object("ack_obj")

    #convenience function to set all vars
    @validate_parameters
    def set_all(
        self, 
        source : non_blank(str),          # type: ignore
        sink   : non_blank(str),          # type: ignore
        pkt_id : strongly_typed(int),     # type: ignore
        state  : strongly_typed(TxState), # type: ignore
        mode   : strongly_typed(TxMode),  # type: ignore
        req_obj, #weak type
        ack_obj  #weak type  
    ) -> None:
        """set all the values of the packet"""
        self.set_path(source, sink)
        self.set_pkt_id(pkt_id)
        self.set_state(state)
        self.set_mode(mode)
        self.set_req_obj(req_obj)
        self.set_ack_obj(ack_obj)

    @validate_parameters
    def set_path(
        self, 
        source : non_blank(str), # type: ignore
        sink   : non_blank(str), # type: ignore
    ) -> None:
        """function to set the path var"""
        self.path = (source, sink)

    def get_path(self) -> tuple:
        """function to get the path var"""
        return self.path

    @validate_parameters
    def set_pkt_id(
        self, 
        pkt_id : strongly_typed(int), # type: ignore
    ) -> None:
        """function to set the pkt_id var"""
        self.pkt_id = pkt_id

    def get_pkt_id(self) -> int:
        """function to get the pkt_id var"""
        return self.pkt_id

    @validate_parameters
    def set_state(
        self, 
        state : strongly_typed(TxState), # type: ignore
    ) -> None:
        """function to set the state var"""
        self.state = state

    def set_state_idle(self) -> None:
        """function to set state to idle 
        """
        self.set_state(TxState.IDLE) 

    def set_state_started(self) -> None:
        """function to set state to started
        """
        self.set_state(TxState.STARTED) 

    def set_state_done(self) -> None:
        """function to set state to done 
        """
        self.set_state(TxState.DONE) 

    def set_state_abort(self) -> None:
        """function to set state to done 
        """
        self.set_state(TxState.ABORT) 

    def get_state(self) -> TxState:
        """function to get the state var"""
        return self.state

    def is_state_idle(self) -> bool:
        """function to check if idle"""
        if self.get_state() == TxState.IDLE:
            return True 
        else:
            return False

    def is_state_started(self) -> bool:
        """function to check if started"""
        if self.get_state() == TxState.STARTED:
            return True 
        else:
            return False
        
    def is_state_done(self) -> bool:
        """function to check if done"""
        if self.get_state() == TxState.DONE:
            return True 
        else:
            return False
        
    def is_state_abort(self) -> bool:
        """function to check if pkt is aborted"""
        if self.get_state() == TxState.ABORT:
            return True 
        else:
            return False
        
    #############################################
    def set_mode(
        self, 
        mode : strongly_typed(TxMode),  # type: ignore
    ) -> None:
        """function to set the mode var"""
        self.mode = mode

    def get_mode(self) -> TxMode:
        """function to get the mode var"""
        return self.mode
    
    def is_ack_required(self) -> bool:
        if (self.get_mode() == TxMode.ACK) or (self.get_mode() == TxMode.ACK):
            return True 
        else:
            return False

    ##################################################
    def set_req_obj(self, req_obj:uvm_object) -> None:
        """function to set the req object var"""
        self.req_obj = req_obj

    def get_req_obj(self) -> uvm_object:
        """function to get the req object var"""
        return self.req_obj

    def set_ack_obj(self, ack_obj:uvm_object) -> None:
        """function to set the ack object var"""
        self.ack_obj = ack_obj

    def get_ack_obj(self) -> uvm_object:
        """function to get the ack object var"""
        return self.ack_obj
