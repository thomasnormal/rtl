class aon_timer_base_test extends cip_base_test #(
    .CFG_T(aon_timer_env_cfg),
    .ENV_T(aon_timer_env)
  );

  `uvm_component_utils(aon_timer_base_test)
  `uvm_component_new

  function void build_phase(uvm_phase phase);
    super.build_phase(phase);
    cfg.en_scb = 0;
    cfg.en_cov = 0;
  endfunction

  virtual function void add_message_demotes(dv_report_catcher catcher);
    string msg;

    super.add_message_demotes(catcher);

    msg = "\s*Unable to locate register 'intr_enable' in block 'aon_timer_reg_block'*";
    catcher.add_change_sev("RegModel", msg, UVM_INFO);
    msg = "name tb\\.dut\\.u_reg\\..* cannot be resolved to a hdl object.*";
    catcher.add_change_sev("UVM/DPI/NOBJ1", msg, UVM_INFO);
  endfunction

endclass : aon_timer_base_test
