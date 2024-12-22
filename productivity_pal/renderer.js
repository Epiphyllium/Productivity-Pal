const { ipcRenderer } = require('electron');

// 获取表单和按钮
const taskForm = document.getElementById('task-form');
const submitButton = taskForm.querySelector('button[type="submit"]');

taskForm.addEventListener('submit', (event) => {

  event.preventDefault(); // 阻止表单默认提交行为

  // 收集表单数据
  const taskData = {
    name: document.getElementById('task-name').value.trim(),
    description: document.getElementById('task-desc').value.trim(),
    dueDate: document.getElementById('due-date').value.trim(),
    reDate: document.getElementById('re-date').value.trim(),
  };

  console.log('Task Data:', taskData);

  // 禁用提交按钮，防止重复提交
  submitButton.disabled = true;
  submitButton.textContent = "Submitting...";

  // 创建 WebSocket 连接
  const ws = new WebSocket('ws://localhost:8080');

  ws.onopen = () => {
    console.log('WebSocket 连接已建立');
    // 发送任务数据
    ws.send(JSON.stringify(taskData));
  };

  ws.onmessage = (event) => {
    console.log('收到服务器消息:', event.data);
    const response = JSON.parse(event.data);
    if (response.status === "success") {
      alert('Task submitted successfully!');
    }
    resetButtonState(); // 恢复按钮状态
    taskForm.reset(); // 清空表单数据
    ws.close(); // 发送完成后关闭连接
  };

  ws.onerror = (error) => {
    console.error('WebSocket 错误:', error);
    alert('Failed to submit the task. Please check the server and try again.');
    resetButtonState(); // 恢复按钮状态
  };

  ws.onclose = () => {
    console.log('WebSocket 连接已关闭');
  };
});

// 恢复按钮状态的函数
function resetButtonState() {
  submitButton.disabled = false;
  submitButton.textContent = "Confirm";
}