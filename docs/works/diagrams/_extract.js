const fs = require('fs');
const md = fs.readFileSync('docs/works/期末项目报告.md', 'utf8');
const re = /```mermaid\n([\s\S]*?)```/g;
let m, i = 0;
const names = ['01-提示词分层', '02-工作流StateGraph', '03-PTOR循环', '04-多模态架构', '05-安全防御纵深'];
while ((m = re.exec(md)) !== null) {
  const name = names[i] || ('diagram-' + (i+1));
  fs.writeFileSync(`docs/works/diagrams/${name}.mmd`, m[1].trim() + '\n', 'utf8');
  console.log('written:', name, '(', m[1].trim().split('\n').length, 'lines )');
  i++;
}
console.log('total mermaid blocks:', i);
