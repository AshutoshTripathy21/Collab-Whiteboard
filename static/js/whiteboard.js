document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("whiteboard");
  const context = canvas.getContext("2d", { willReadFrequently: true }); // Set willReadFrequently to true
  const socketio = io();

  let drawing = false;
  let currentTool = "pen";
  let currentColor = "#000000";

  canvas.addEventListener("mousedown", startDrawing);
  canvas.addEventListener("mouseup", stopDrawing);
  canvas.addEventListener("mouseout", stopDrawing);
  canvas.addEventListener("mousemove", draw);

  function startDrawing(e) {
    drawing = true;
    draw(e);
  }

  function stopDrawing() {
    drawing = false;
    context.beginPath();
  }

  function draw(e) {
    if (!drawing) return;

    context.lineWidth = 2;
    context.lineCap = "round";
    context.strokeStyle = currentColor;

    const { offsetX, offsetY } = e;

    context.lineTo(offsetX, offsetY);
    context.stroke();

    const data = {
      offsetX,
      offsetY,
      drawing: true,
      tool: currentTool,
      color: currentColor
    };
    socketio.emit("drawing", data);
  }

  socketio.on("drawing", (data) => {
    const { offsetX, offsetY, tool, color } = data;

    context.lineWidth = 2;
    context.lineCap = "round";
    context.strokeStyle = color;

    if (tool === "pen" || tool === "pencil") {
      context.lineTo(offsetX, offsetY);
      context.stroke();
    } else if (tool === "text") {
      // Handle text drawing
    } else if (tool === "eraser") {
      context.clearRect(offsetX - 5, offsetY - 5, 10, 10);
    }
  });

  document.getElementById("colorPicker").addEventListener("input", (e) => {
    currentColor = e.target.value;
  });

  // Other functions for tool selection, undo, redo, etc.
});
