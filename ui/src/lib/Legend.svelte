<div class="overlay legend">
  <div class="title">LEGEND</div>
  <div class="row"><span class="dot star"></span> system</div>
  <div class="row"><span class="dot binary"></span> binary system</div>
  <div class="row"><span class="dot host"></span> junction host</div>
  <div class="row"><span class="line"></span> wormhole link</div>
</div>

<style>
  .legend {
    right: 12px;
    bottom: 12px;
  }
  .row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 2px 0;
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
  }
  .star {
    background: #dfe6f0;
  }
  .binary {
    background: #9fd0ff;
  }
  .host {
    background: transparent;
    border: 1.5px solid #caa64a;
  }
  .line {
    width: 16px;
    height: 0;
    border-top: 1px solid #33476b;
    display: inline-block;
  }
</style>
