module i2c_micro_arch_bind;

  bind i2c i2c_micro_arch_checker u_i2c_micro_arch_checker (
    .clk_i(clk_i),
    .rst_ni(rst_ni),
    .cio_scl_en_o(cio_scl_en_o),
    .cio_sda_en_o(cio_sda_en_o),
    .micro_arch_if(u_i2c_micro_arch_if)
  );

endmodule
