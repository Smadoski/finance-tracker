'use strict';
(() => {
  const model = JSON.parse(document.getElementById('health-model').textContent);
  const inputs = [...document.querySelectorAll('.income-source')];
  const types = [...document.querySelectorAll('.income-type')];
  const preset = document.getElementById('scenario-preset');
  const output = document.getElementById('scenario-results');
  const format = value => value === null ? 'Not calculable / no depletion' : value.toLocaleString(undefined, {minimumFractionDigits:2,maximumFractionDigits:2});
  function update() {
    const enabled = new Set(inputs.filter(i=>i.checked).map(i=>i.dataset.key));
    let income=0, extraordinary=0;
    model.income_sources.forEach(s=>{if(enabled.has(s.key)){if(s.type==='extraordinary')extraordinary+=s.monthly;else income+=s.monthly;}});
    const cost=model.normal_monthly_cost, surplus=income-cost, drawdown=Math.max(-surplus,0);
    const values=[['Monthly income',income],['Normal monthly expenditure',cost],['Monthly surplus / shortfall',surplus],['Annual surplus / shortfall',surplus*12],['Income coverage %',cost?income/cost*100:null],['Monthly capital requirement',drawdown],['Financial capital runway (months)',drawdown?model.available_financial_capital/drawdown:null],['Extraordinary observed monthly average (separate)',extraordinary]];
    output.replaceChildren(...values.map(([label,value])=>{const box=document.createElement('div');box.className='metric';const name=document.createElement('span'),number=document.createElement('b');name.textContent=label;number.textContent=format(value);box.append(name,number);return box;}));
    types.forEach(t=>{const matches=inputs.filter(i=>i.dataset.type===t.dataset.type);t.checked=matches.length>0&&matches.every(i=>i.checked);t.indeterminate=matches.some(i=>i.checked)&&!t.checked;});
  }
  inputs.forEach(i=>i.addEventListener('change',()=>{preset.value='custom';update();}));
  types.forEach(t=>t.addEventListener('change',()=>{inputs.filter(i=>i.dataset.type===t.dataset.type).forEach(i=>i.checked=t.checked);preset.value='custom';update();}));
  preset.addEventListener('change',()=>{if(preset.value==='custom')return;inputs.forEach(i=>{const t=i.dataset.type;i.checked=t!=='extraordinary'&&(preset.value==='current'||preset.value==='no_investment'&&t!=='investment'||preset.value==='no_salary'&&t!=='salary'||preset.value==='pension'&&['state_pension','private_pension'].includes(t)||preset.value==='salary_pension'&&['salary','state_pension','private_pension'].includes(t));});update();});
  update();
})();
