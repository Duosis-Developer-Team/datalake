\restrict TDszizIJhQjvJXCRRYA9Txm8vEQ7yQNA5q2owB2n3Fcbqcq1BZZqgldCJZGPk5c
CREATE TABLE public.ibm_lpar_net_virtual (
    servername character varying(255),
    lparname character varying(255),
    location character varying(255),
    vlanid integer,
    vswitchid integer,
    physicallocation character varying(255),
    isportvlanid boolean,
    viosid integer,
    sharedethernetadapterid character varying(255),
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
ALTER TABLE ONLY public.ibm_lpar_net_virtual
    ADD CONSTRAINT unique_ibm_lpar_net_virtual_metric_entry UNIQUE (lparname, vlanid, "time");
\unrestrict TDszizIJhQjvJXCRRYA9Txm8vEQ7yQNA5q2owB2n3Fcbqcq1BZZqgldCJZGPk5c
