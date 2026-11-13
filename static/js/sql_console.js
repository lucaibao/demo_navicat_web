let currentTaskId = null;
const baseUrl = "/api/sql";
const resultBox = document.getElementById('rightPane');
const configPanel = document.getElementById('configPanel');
const toggleBtn = document.getElementById('toggleBtn');
const fullscreenBtn = document.getElementById('fullscreenBtn');
const splitWrap = document.getElementById('splitWrap');
const splitter = document.getElementById('splitter');
const leftPane = document.getElementById('leftPane');

// ========== 拖拽分割线 ==========
let isDragging = false;
splitter.addEventListener('mousedown', (e) => {
  isDragging = true;
  document.body.style.cursor = 'col-resize';
  document.body.style.userSelect = 'none';
});
document.addEventListener('mousemove', (e) => {
  if (!isDragging) return;
  const rect = splitWrap.getBoundingClientRect();
  let leftW = e.clientX - rect.left;
  if (leftW < 200) leftW = 200;
  if (leftW > rect.width - 200) leftW = rect.width - 200;
  leftPane.style.width = leftW + 'px';
});
document.addEventListener('mouseup', () => {
  isDragging = false;
  document.body.style.cursor = '';
  document.body.style.userSelect = '';
});

// ========== 全屏切换 ==========
fullscreenBtn.onclick = async () => {
  if (!document.fullscreenElement) {
    await splitWrap.requestFullscreen?.();
    fullscreenBtn.innerText = "退出全屏";
  } else {
    await document.exitFullscreen?.();
    fullscreenBtn.innerText = "全屏";
  }
};
document.addEventListener('fullscreenchange', () => {
  if (!document.fullscreenElement) {
    fullscreenBtn.innerText = "全屏";
  }
});

// ========== 配置面板折叠 ==========
toggleBtn.onclick = function () {
  configPanel.classList.toggle("open");
  if (configPanel.classList.contains("open")) {
    toggleBtn.innerText = "收起配置 ▲";
  } else {
    toggleBtn.innerText = "展开配置 ▼";
  }
};

// ========== 加载DB_前缀变量列表，填充所有下拉框 ==========
async function loadDBEnvKeys() {
  try {
    const resp = await fetch("/api/db-env");
    const cfg = await resp.json();
    const keys = cfg.db_keys || [];
    const selectList = [
      document.getElementById("hostKey"),
      document.getElementById("portKey"),
      document.getElementById("userKey"),
      document.getElementById("pwdKey"),
      document.getElementById("dbnameKey"),
      document.getElementById("schemaKey")
    ];
    // 给每个下拉追加选项
    for(const sel of selectList){
      for(const k of keys){
        const opt = document.createElement("option");
        opt.value = k;
        opt.innerText = k;
        sel.appendChild(opt);
      }
      // 切换下拉时清空输入框、置灰
      sel.onchange = function(){
        const inputDom = document.getElementById(sel.id.replace("Key",""));
        if(this.value){
          inputDom.value = "";
          inputDom.disabled = true;
        }else{
          inputDom.disabled = false;
        }
      }
    }
  } catch (err) {
    console.warn("读取DB环境变量列表失败", err);
  }
}
loadDBEnvKeys();

// ========== 获取SQL：优先取选中文本，没有选中就取全部内容 ==========
function getSql() {
  const ta = document.getElementById('sqlTextarea');
  const selectedText = ta.value.substring(ta.selectionStart, ta.selectionEnd).trim();
  if (selectedText) {
    return selectedText;
  }
  return ta.value.trim();
}

// 按分号切割多条SQL
function splitSqlBatch(sqlText) {
  const list = [];
  const parts = sqlText.split(/;/);
  for (const p of parts) {
    const s = p.trim();
    if (s) {
      list.push(s + ";");
    }
  }
  return list;
}

// 格式化时间字段（去掉T）
function formatDateTime(val) {
  if (typeof val === 'string' && val.includes('T')) {
    return val.replace('T', ' ');
  }
  return val === null ? "" : val;
}

// 渲染结果表格
function appendResultHtml(sqlText, statusText, rs) {
  const wrap = document.createElement('div');
  wrap.className = "sql-item";
  let html = `<div class="sql-title">【SQL】${sqlText}</div>`;
  html += `<div class="sql-status ${statusText.startsWith('✅') ? 'ok' : 'err'}">${statusText}</div>`;

  if (rs && rs.columns && rs.rows) {
    html += `<table class="result-table">`;
    html += `<thead><tr>`;
    for (const col of rs.columns) {
      html += `<th>${col}</th>`;
    }
    html += `</tr></thead><tbody>`;
    for (const row of rs.rows) {
      html += `<tr>`;
      for (const cell of row) {
        html += `<td>${formatDateTime(cell)}</td>`;
      }
      html += `</tr>`;
    }
    html += `</tbody></table>`;
    html += `<div class="result-tip">总行数：${rs.row_count || rs.rows.length}，截断：${!!rs.truncated}</div>`;
  } else if (rs && rs.affected_rows !== undefined) {
    html += `<div class="result-tip">影响行数：${rs.affected_rows}</div>`;
  } else {
    html += `<pre class="raw-result">${JSON.stringify(rs, null, 2)}</pre>`;
  }
  wrap.innerHTML = html;
  resultBox.appendChild(wrap);
  // 滚动到底部
  resultBox.scrollTop = resultBox.scrollHeight;
}

// 清空右侧结果面板函数
function clearResult() {
  resultBox.innerHTML = "";
}

// 轮询等待任务执行完成
async function waitTaskDone(taskId) {
  while (true) {
    const res = await fetch(`${baseUrl}/status/${taskId}`);
    const data = await res.json();
    if (data.status === "pending" || data.status === "running") {
      await new Promise(r => setTimeout(r, 700));
      continue;
    }
    return data;
  }
}

// 执行SQL入口
async function runSql() {
  const sqlRaw = getSql();
  if (!sqlRaw) {
    resultBox.innerHTML = `<div class="err">❌ 请输入或者选中SQL语句</div>`;
    return;
  }
  const sqlList = splitSqlBatch(sqlRaw);
  if (sqlList.length === 0) return;

  let hasRiskConfirmed = false;
  const maxRowsInput = document.getElementById('maxRows');
  const maxRowsVal = maxRowsInput.value.trim() === '' ? null : Number(maxRowsInput.value);
  const timeoutInput = document.getElementById('timeoutSec');
  const timeoutVal = timeoutInput.value.trim() === '' ? null : Number(timeoutInput.value);

  // 传给后端：变量KEY + 手动填写值
  const baseReq = {
    db_type: document.getElementById('dbType').value,
    host_key: document.getElementById('hostKey').value,
    host: document.getElementById('host').value,
    port_key: document.getElementById('portKey').value,
    port: document.getElementById('port').value,
    user_key: document.getElementById('userKey').value,
    user: document.getElementById('user').value,
    pwd_key: document.getElementById('pwdKey').value,
    password: document.getElementById('pwd').value,
    dbname_key: document.getElementById('dbnameKey').value,
    database: document.getElementById('dbname').value,
    schema_key: document.getElementById('schemaKey').value,
    schema: document.getElementById('schema').value,
    timeout_sec: timeoutVal,
    max_rows: maxRowsVal,
    confirm_risk: false
  };

  for (const oneSql of sqlList) {
    const req = { ...baseReq, sql: oneSql, confirm_risk: hasRiskConfirmed };
    try {
      const resp = await fetch(`${baseUrl}/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(req)
      });
      const data = await resp.json();
      if (!resp.ok) {
        if (resp.status === 400 && data.detail?.includes("检测到高危SQL")) {
          const ok = confirm(`⚠️ 高危SQL：\n${data.detail}\n确认继续执行这批SQL吗？`);
          if (ok) {
            hasRiskConfirmed = true;
            req.confirm_risk = true;
            const resp2 = await fetch(`${baseUrl}/run`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(req)
            });
            const data2 = await resp2.json();
            if (!resp2.ok) {
              appendResultHtml(oneSql, "❌ 高危SQL提交失败", data2);
              break;
            }
            currentTaskId = data2.task_id;
          } else {
            appendResultHtml(oneSql, "❌ 用户取消高危SQL执行", null);
            break;
          }
        } else {
          appendResultHtml(oneSql, "❌ 请求失败", data);
          break;
        }
      } else {
        currentTaskId = data.task_id;
      }
      const taskResult = await waitTaskDone(currentTaskId);
      console.log("后端返回任务结果：", taskResult);
      if (taskResult.status === "finished") {
        appendResultHtml(oneSql, "✅ 执行成功", taskResult.result);
      } else if (taskResult.status === "failed") {
        appendResultHtml(oneSql, `❌ ${taskResult.status}`, taskResult.error);
      } else {
        appendResultHtml(oneSql, `❌ 未知状态:${taskResult.status}`, taskResult);
        break;
      }
    } catch (err) {
      appendResultHtml(oneSql, "❌ 网络异常", err.message);
      break;
    }
  }
}

// 取消任务
async function cancelTask() {
  if (!currentTaskId) return;
  try {
    await fetch(`${baseUrl}/cancel/${currentTaskId}`, { method: "POST" });
    appendResultHtml("【取消指令】", "✅ 已发送取消请求", null);
  } catch (e) {
    appendResultHtml("【取消指令】", "❌ 取消失败：" + e.message, null);
  }
}

// 绑定页面按钮
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('runBtn').onclick = runSql;
  document.getElementById('cancelBtn').onclick = cancelTask;
  // 绑定清空按钮
  document.getElementById('clearBtn').onclick = clearResult;
});
