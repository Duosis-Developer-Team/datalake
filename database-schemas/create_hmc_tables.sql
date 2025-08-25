-- public.ibm_lpar_general definition

-- Drop table

-- DROP TABLE public.ibm_lpar_general;

CREATE TABLE public.ibm_lpar_general (
	lpar_details_servername varchar(255) NULL,
	lpar_details_lparname varchar(255) NULL,
	lpar_details_id int4 NULL,
	lpar_details_name varchar(255) NULL,
	lpar_details_state varchar(50) NULL,
	lpar_details_type varchar(50) NULL,
	lpar_details_ostype varchar(100) NULL,
	lpar_details_affinityscore int4 NULL,
	lpar_processor_servername varchar(255) NULL,
	lpar_processor_lparname varchar(255) NULL,
	lpar_processor_poolid int4 NULL,
	lpar_processor_weight int4 NULL,
	lpar_processor_mode varchar(50) NULL,
	lpar_processor_maxvirtualprocessors float8 NULL,
	lpar_processor_currentvirtualprocessors float8 NULL,
	lpar_processor_maxprocunits float8 NULL,
	lpar_processor_entitledprocunits float8 NULL,
	lpar_processor_utilizedprocunitsdeductidle float8 NULL,
	lpar_processor_utilizedprocunits float8 NULL,
	lpar_processor_utilizedcappedprocunits float8 NULL,
	lpar_processor_utilizeduncappedprocunits float8 NULL,
	lpar_processor_idleprocunits float8 NULL,
	lpar_processor_donatedprocunits float8 NULL,
	lpar_processor_timespentwaitingfordispatch float8 NULL,
	lpar_processor_timeperinstructionexecution float8 NULL,
	lpar_memory_servername varchar(255) NULL,
	lpar_memory_lparname varchar(255) NULL,
	lpar_memory_logicalmem float8 NULL,
	lpar_memory_backedphysicalmem float8 NULL,
	lpar_memory_virtualpersistentmem float8 NULL,
	lpar_storage_virtual_servername varchar(255) NULL,
	lpar_storage_virtual_lparname varchar(255) NULL,
	lpar_storage_virtual_id varchar(255) NULL,
	lpar_storage_virtual_location varchar(255) NULL,
	lpar_storage_virtual_viosid int4 NULL,
	lpar_storage_virtual_type varchar(50) NULL,
	lpar_storage_virtual_physicallocation varchar(255) NULL,
	lpar_storage_virtual_numofreads float8 NULL,
	lpar_storage_virtual_numofwrites float8 NULL,
	lpar_storage_virtual_readbytes float8 NULL,
	lpar_storage_virtual_writebytes float8 NULL,
	servername varchar(255) NULL,
	lparname varchar(255) NULL,
	"time" timestamptz NULL
);


-- public.ibm_lpar_net_virtual definition

-- Drop table

-- DROP TABLE public.ibm_lpar_net_virtual;

CREATE TABLE public.ibm_lpar_net_virtual (
	servername varchar(255) NULL,
	lparname varchar(255) NULL,
	"location" varchar(255) NULL,
	vlanid int4 NULL,
	vswitchid int4 NULL,
	physicallocation varchar(255) NULL,
	isportvlanid bool NULL,
	viosid int4 NULL,
	sharedethernetadapterid varchar(255) NULL,
	receivedpackets float8 NULL,
	sentpackets float8 NULL,
	droppedpackets float8 NULL,
	sentbytes float8 NULL,
	receivedbytes float8 NULL,
	receivedphysicalpackets float8 NULL,
	sentphysicalpackets float8 NULL,
	droppedphysicalpackets float8 NULL,
	sentphysicalbytes float8 NULL,
	receivedphysicalbytes float8 NULL,
	transferredbytes float8 NULL,
	transferredphysicalbytes float8 NULL,
	"time" timestamptz NULL
);


-- public.ibm_lpar_storage_vfc definition

-- Drop table

-- DROP TABLE public.ibm_lpar_storage_vfc;

CREATE TABLE public.ibm_lpar_storage_vfc (
	servername varchar(255) NULL,
	lparname varchar(255) NULL,
	"location" varchar(255) NULL,
	viosid int4 NULL,
	id varchar(255) NULL,
	wwpn varchar(255) NULL,
	wwpn2 varchar(255) NULL,
	physicallocation varchar(255) NULL,
	physicalportwwpn float8 NULL,
	numofreads float8 NULL,
	numofwrites float8 NULL,
	readbytes float8 NULL,
	writebytes float8 NULL,
	runningspeed float8 NULL,
	"time" timestamptz NULL
);


-- public.ibm_server_general definition

-- Drop table

-- DROP TABLE public.ibm_server_general;

CREATE TABLE public.ibm_server_general (
	server_details_servername varchar(255) NULL,
	server_details_utilizedprocunits float8 NULL,
	server_details_assignedmem float8 NULL,
	server_details_mtm varchar(255) NULL,
	server_details_name varchar(255) NULL,
	server_details_apiversion varchar(255) NULL,
	server_details_metric varchar(255) NULL,
	server_details_frequency int4 NULL,
	server_details_nextract varchar(255) NULL,
	server_processor_servername varchar(255) NULL,
	server_processor_totalprocunits float8 NULL,
	server_processor_utilizedprocunits float8 NULL,
	server_processor_utilizedprocunitsdeductidle float8 NULL,
	server_processor_availableprocunits float8 NULL,
	server_processor_configurableprocunits float8 NULL,
	server_memory_servername varchar(255) NULL,
	server_memory_totalmem float8 NULL,
	server_memory_availablemem float8 NULL,
	server_memory_configurablemem float8 NULL,
	server_memory_assignedmemtolpars float8 NULL,
	server_memory_virtualpersistentmem float8 NULL,
	server_physicalprocessorpool_servername varchar(255) NULL,
	server_physicalprocessorpool_assignedprocunits float8 NULL,
	server_physicalprocessorpool_utilizedprocunits float8 NULL,
	server_physicalprocessorpool_availableprocunits float8 NULL,
	server_physicalprocessorpool_configuredprocunits float8 NULL,
	server_physicalprocessorpool_borrowedprocunits float8 NULL,
	server_sharedprocessorpool_servername varchar(255) NULL,
	server_sharedprocessorpool_pool int4 NULL,
	server_sharedprocessorpool_poolname varchar(255) NULL,
	server_sharedprocessorpool_id int4 NULL,
	server_sharedprocessorpool_name varchar(255) NULL,
	server_sharedprocessorpool_assignedprocunits float8 NULL,
	server_sharedprocessorpool_utilizedprocunits float8 NULL,
	server_sharedprocessorpool_availableprocunits float8 NULL,
	server_sharedprocessorpool_configuredprocunits float8 NULL,
	server_sharedprocessorpool_borrowedprocunits float8 NULL,
	servername varchar(255) NULL,
	"time" timestamptz NULL,
	server_details_uptime varchar(255) NULL
);


-- public.ibm_server_power definition

-- Drop table

-- DROP TABLE public.ibm_server_power;

CREATE TABLE public.ibm_server_power (
	server_name varchar(255) NULL,
	atom_id varchar(255) NULL,
	"timestamp" timestamp NULL,
	power_watts int4 NULL,
	mb0 int4 NULL,
	mb1 int4 NULL,
	mb2 int4 NULL,
	mb3 int4 NULL,
	cpu0 int4 NULL,
	cpu1 int4 NULL,
	cpu2 int4 NULL,
	cpu3 int4 NULL,
	cpu4 int4 NULL,
	cpu5 int4 NULL,
	cpu6 int4 NULL,
	cpu7 int4 NULL,
	inlet_temp int4 NULL
);


-- public.ibm_vios_general definition

-- Drop table

-- DROP TABLE public.ibm_vios_general;

CREATE TABLE public.ibm_vios_general (
	vios_details_servername varchar(255) NULL,
	vios_details_viosname varchar(255) NULL,
	vios_details_viosid int4 NULL,
	vios_details_viosstate varchar(255) NULL,
	vios_details_affinityscore int4 NULL,
	vios_memory_servername varchar(255) NULL,
	vios_memory_viosname varchar(255) NULL,
	vios_memory_assignedmem float8 NULL,
	vios_memory_utilizedmem float8 NULL,
	vios_memory_virtualpersistentmem float8 NULL,
	vios_processor_servername varchar(255) NULL,
	vios_processor_viosname varchar(255) NULL,
	vios_processor_poolid int4 NULL,
	vios_processor_weight int4 NULL,
	vios_processor_mode varchar(255) NULL,
	vios_processor_maxvirtualprocessors float8 NULL,
	vios_processor_currentvirtualprocessors float8 NULL,
	vios_processor_maxprocunits float8 NULL,
	vios_processor_entitledprocunits float8 NULL,
	vios_processor_utilizedprocunits float8 NULL,
	vios_processor_utilizedprocunitsdeductidle float8 NULL,
	vios_processor_utilizedcappedprocunits float8 NULL,
	vios_processor_utilizeduncappedprocunits float8 NULL,
	vios_processor_idleprocunits float8 NULL,
	vios_processor_donatedprocunits float8 NULL,
	vios_processor_timespentwaitingfordispatch float8 NULL,
	vios_processor_timeperinstructionexecution float8 NULL,
	vios_network_lpars_servername varchar(255) NULL,
	vios_network_lpars_viosname varchar(255) NULL,
	vios_network_lpars_clientlpars int4 NULL,
	vios_network_shared_servername varchar(255) NULL,
	vios_network_shared_viosname varchar(255) NULL,
	vios_network_shared_id varchar(255) NULL,
	vios_network_shared_location varchar(255) NULL,
	vios_network_shared_type varchar(255) NULL,
	vios_network_shared_physicallocation varchar(255) NULL,
	vios_network_shared_receivedpackets float8 NULL,
	vios_network_shared_sentpackets float8 NULL,
	vios_network_shared_droppedpackets float8 NULL,
	vios_network_shared_sentbytes float8 NULL,
	vios_network_shared_receivedbytes float8 NULL,
	vios_network_shared_transferredbytes float8 NULL,
	vios_storage_lpars_servername varchar(255) NULL,
	vios_storage_lpars_viosname varchar(255) NULL,
	vios_storage_lpars_clientlpars int4 NULL,
	servername varchar(255) NULL,
	viosname varchar(255) NULL,
	"time" timestamptz NULL
);


-- public.ibm_vios_network_generic definition

-- Drop table

-- DROP TABLE public.ibm_vios_network_generic;

CREATE TABLE public.ibm_vios_network_generic (
	servername varchar(255) NULL,
	viosname varchar(255) NULL,
	id varchar(255) NULL,
	"location" varchar(255) NULL,
	"type" varchar(255) NULL,
	physicallocation varchar(255) NULL,
	receivedpackets float8 NULL,
	sentpackets float8 NULL,
	droppedpackets float8 NULL,
	sentbytes float8 NULL,
	receivedbytes float8 NULL,
	transferredbytes float8 NULL,
	"time" timestamptz NULL
);


-- public.ibm_vios_network_virtual definition

-- Drop table

-- DROP TABLE public.ibm_vios_network_virtual;

CREATE TABLE public.ibm_vios_network_virtual (
	servername varchar(255) NULL,
	viosname varchar(255) NULL,
	"location" varchar(255) NULL,
	vswitchid int4 NULL,
	vlanid int4 NULL,
	physicallocation varchar(255) NULL,
	isportvlanid bool NULL,
	receivedpackets float8 NULL,
	sentpackets float8 NULL,
	droppedpackets float8 NULL,
	sentbytes float8 NULL,
	receivedbytes float8 NULL,
	receivedphysicalpackets float8 NULL,
	sentphysicalpackets float8 NULL,
	droppedphysicalpackets float8 NULL,
	sentphysicalbytes float8 NULL,
	receivedphysicalbytes float8 NULL,
	transferredbytes float8 NULL,
	transferredphysicalbytes float8 NULL,
	"time" timestamptz NULL
);


-- public.ibm_vios_storage_fc definition

-- Drop table

-- DROP TABLE public.ibm_vios_storage_fc;

CREATE TABLE public.ibm_vios_storage_fc (
	servername varchar(255) NULL,
	viosname varchar(255) NULL,
	id varchar(255) NULL,
	"location" varchar(255) NULL,
	wwpn float8 NULL,
	physicallocation varchar(255) NULL,
	numofports int4 NULL,
	numofreads float8 NULL,
	numofwrites float8 NULL,
	readbytes float8 NULL,
	writebytes float8 NULL,
	runningspeed float8 NULL,
	"time" timestamptz NULL
);


-- public.ibm_vios_storage_physical definition

-- Drop table

-- DROP TABLE public.ibm_vios_storage_physical;

CREATE TABLE public.ibm_vios_storage_physical (
	servername varchar(255) NULL,
	viosname varchar(255) NULL,
	id varchar(255) NULL,
	"location" varchar(255) NULL,
	"type" varchar(50) NULL,
	physicallocation varchar(255) NULL,
	numofreads float8 NULL,
	numofwrites float8 NULL,
	readbytes float8 NULL,
	writebytes float8 NULL,
	"time" timestamptz NULL
);


-- public.ibm_vios_storage_virtual definition

-- Drop table

-- DROP TABLE public.ibm_vios_storage_virtual;

CREATE TABLE public.ibm_vios_storage_virtual (
	servername varchar(255) NULL,
	viosname varchar(255) NULL,
	id varchar(255) NULL,
	"location" varchar(255) NULL,
	"type" varchar(50) NULL,
	physicallocation varchar(255) NULL,
	numofreads float8 NULL,
	numofwrites float8 NULL,
	readbytes float8 NULL,
	writebytes float8 NULL,
	"time" timestamptz NULL
);