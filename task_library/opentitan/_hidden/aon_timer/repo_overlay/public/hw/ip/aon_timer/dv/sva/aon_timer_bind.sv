module aon_timer_bind;

  bind aon_timer tlul_assert #(
    .EndpointType("Device")
  ) tlul_assert_device (
    .clk_i,
    .rst_ni,
    .h2d  (tl_i),
    .d2h  (tl_o)
  );

  aon_timer_micro_arch_bind u_aon_timer_micro_arch_bind();

endmodule
