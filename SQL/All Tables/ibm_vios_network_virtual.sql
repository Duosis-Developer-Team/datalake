\restrict kdScg80fcWCV2ib4den8SI0pa2KzDddINCxppJkLp0rTfesYmwA3fWyDBqkbukJ
CREATE TABLE public.ibm_vios_network_virtual (
    servername character varying(255),
    viosname character varying(255),
    location character varying(255),
    vswitchid integer,
    vlanid integer,
    physicallocation character varying(255),
    isportvlanid boolean,
    receivedpackets double precision,
    sentpackets double precision,
    droppedpackets double precision,
    sentbytes double precision,
    receivedbytes double precision,
    receivedphysicalpackets double precision,
    sentphysicalpackets double precision,
    droppedphysicalpackets double precision,
    sentphysicalbytes double precision,
    receivedphysicalbytes double precision,
    transferredbytes double precision,
    transferredphysicalbytes double precision,
    "time" timestamp with time zone
);
ALTER TABLE ONLY public.ibm_vios_network_virtual
    ADD CONSTRAINT unique_ibm_vios_network_virtual_metric_entry UNIQUE (viosname, vswitchid, vlanid, "time");
\unrestrict kdScg80fcWCV2ib4den8SI0pa2KzDddINCxppJkLp0rTfesYmwA3fWyDBqkbukJ
