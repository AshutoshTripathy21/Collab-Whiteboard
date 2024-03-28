document.addEventListener("DOMContentLoaded", () => {
  const canvas = document.getElementById("whiteboard");
  const context = canvas.getContext("2d", { willReadFrequently: true }); // Set willReadFrequently to true
  const socketio = io();

  let drawing = false;
  let currentTool = "pen";
  let currentColor = "#000000";
  let penThickness = 2; // Default pen thickness
  let eraserThickness = 10; // Default eraser thickness
  let pencilThickness = 1; // Default pencil thickness
  let actions = []; // Array to store drawing actions for undo/redo
  let currentIndex = -1; // Index to track the current action

  canvas.addEventListener("mousedown", handleMouseDown);
  canvas.addEventListener("mouseup", handleMouseUp);
  canvas.addEventListener("mouseout", handleMouseOut);
  canvas.addEventListener("mousemove", handleMouseMove);

  function handleMouseDown(e) {
    if (currentTool === "text") {
      text = prompt("Enter text:");
      if (text !== null && text.trim() !== "") {
        textX = e.offsetX;
        textY = e.offsetY;
        writeText(text, textX, textY);
      }
    } else if (currentTool === "circle") {
      startDrawingCircle(e);
    } else if (currentTool === "square") {
      startDrawingSquare(e);
    } else {
      drawing = true;
      startDrawing(e);
    }
  }

  function handleMouseUp(e) {
    if (!drawing) return;
    stopDrawing();
  }

  function handleMouseOut() {
    if (!drawing) return;
    stopDrawing();
  }

  function handleMouseMove(e) {
    if (!drawing) return;
    draw(e);
  }

  function startDrawing(e) {
    drawing = true;
    draw(e);
  }

  function stopDrawing() {
    drawing = false;
    context.beginPath();
    // If drawing has occurred, push the current state to the actions array
    if (currentIndex < actions.length - 1) {
      actions = actions.slice(0, currentIndex + 1);
    }
    actions.push(context.getImageData(0, 0, canvas.width, canvas.height));
    currentIndex++;
  }

  function draw(e) {
    if (!drawing) return;

    let thickness;
    if (currentTool === "pen") {
      thickness = penThickness;
    } else if (currentTool === "pencil") {
      thickness = pencilThickness;
    } else if (currentTool === "eraser") {
      thickness = eraserThickness;
    }

    context.lineWidth = thickness;
    context.lineCap = "round";
    context.strokeStyle = currentTool === "eraser" ? "#FFFFFF" : currentColor;

    const { offsetX, offsetY } = e;

    context.lineTo(offsetX, offsetY);
    context.stroke();

    const data = {
      offsetX,
      offsetY,
      drawing: true,
      tool: currentTool,
      color: currentTool === "eraser" ? "#FFFFFF" : currentColor,
      thickness: thickness
    };
    socketio.emit("drawing", data);
  }

  function writeText(text, x, y) {
    context.fillStyle = currentColor;
    context.font = "16px Arial";
    context.fillText(text, x, y);
    const data = {
      offsetX: x,
      offsetY: y,
      drawing: true,
      tool: "text",
      color: currentColor,
      text: text
    };
    socketio.emit("drawing", data);
    actions.push(context.getImageData(0, 0, canvas.width, canvas.height));
    currentIndex++;
  }

  function startDrawingCircle(e) {
    drawing = true;
    circleStartX = e.offsetX;
    circleStartY = e.offsetY;
    canvas.addEventListener("mousemove", drawCircle);
    canvas.addEventListener("mouseup", stopDrawingCircle);
  }

  function drawCircle(e) {
    if (!drawing) return;
    context.clearRect(0, 0, canvas.width, canvas.height);
    drawActions();
    const radius = Math.sqrt(Math.pow(e.offsetX - circleStartX, 2) + Math.pow(e.offsetY - circleStartY, 2));
    context.beginPath();
    context.arc(circleStartX, circleStartY, radius, 0, 2 * Math.PI);
    context.stroke();
  }

  function stopDrawingCircle() {
    drawing = false;
    canvas.removeEventListener("mousemove", drawCircle);
    canvas.removeEventListener("mouseup", stopDrawingCircle);
    const data = {
      offsetX: circleStartX,
      offsetY: circleStartY,
      drawing: true,
      tool: "circle",
      color: currentColor,
      radius: Math.sqrt(Math.pow(circleStartX - circleEndX, 2) + Math.pow(circleStartY - circleEndY, 2))
    };
    socketio.emit("drawing", data);
    actions.push(context.getImageData(0, 0, canvas.width, canvas.height));
    currentIndex++;
  }

  function startDrawingSquare(e) {
    drawing = true;
    squareStartX = e.offsetX;
    squareStartY = e.offsetY;
    canvas.addEventListener("mousemove", drawSquare);
    canvas.addEventListener("mouseup", stopDrawingSquare);
  }

  function drawSquare(e) {
    if (!drawing) return;
    context.clearRect(0, 0, canvas.width, canvas.height);
    drawActions();
    const width = Math.abs(e.offsetX - squareStartX);
    const height = Math.abs(e.offsetY - squareStartY);
    const size = Math.min(width, height);
    context.beginPath();
    context.rect(squareStartX, squareStartY, size, size);
    context.stroke();
  }

  function stopDrawingSquare() {
    drawing = false;
    canvas.removeEventListener("mousemove", drawSquare);
    canvas.removeEventListener("mouseup", stopDrawingSquare);
    const data = {
      offsetX: squareStartX,
      offsetY: squareStartY,
      drawing: true,
      tool: "square",
      color: currentColor,
      size: Math.abs(squareStartX - squareEndX)
    };
    socketio.emit("drawing", data);
    actions.push(context.getImageData(0, 0, canvas.width, canvas.height));
    currentIndex++;
  }
  
  socketio.on("drawing", (data) => {
    const { offsetX, offsetY, tool, color, thickness, text, radius, size } = data;

    context.lineWidth = thickness;
    context.lineCap = "round";
    context.strokeStyle = color;

    if (tool === "pen" || tool === "pencil" || tool === "eraser") {
      context.lineTo(offsetX, offsetY);
      context.stroke();
    } else if (tool === "text") {
      context.fillStyle = color;
      context.font = "16px Arial";
      context.fillText(text, offsetX, offsetY);
    } else if (tool === "circle") {
      context.beginPath();
      context.arc(offsetX, offsetY, radius, 0, 2 * Math.PI);
      context.stroke();
    } else if (tool === "square") {
      context.beginPath();
      context.rect(offsetX, offsetY, size, size);
      context.stroke();
    }
  });

  document.getElementById("colorPicker").addEventListener("input", (e) => {
    currentColor = e.target.value;
  });

  document.getElementById("tool-select").addEventListener("change", (e) => {
    currentTool = e.target.value;
  });

  document.getElementById("thickness").addEventListener("input", (e) => {
    if (currentTool === "pen") {
      penThickness = parseInt(e.target.value);
    } else if (currentTool === "pencil") {
      pencilThickness = parseInt(e.target.value);
    }
  });

  document.getElementById("undoBtn").addEventListener("click", undo);
  document.getElementById("redoBtn").addEventListener("click", redo);

  function undo() {
    if (currentIndex > 0) {
      currentIndex--;
      context.putImageData(actions[currentIndex], 0, 0);
    }
  }

  function redo() {
    if (currentIndex < actions.length - 1) {
      currentIndex++;
      context.putImageData(actions[currentIndex], 0, 0);
    }
  }

  function drawActions() {
    actions.forEach((action) => {
      context.putImageData(action, 0, 0);
    });
  }

  // Other functions for tool selection, undo, redo, etc.
});
