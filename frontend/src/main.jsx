import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import {
  Chart as ChartJS,
  CategoryScale, LinearScale, BarElement, ArcElement,
  LineElement, PointElement, Title, Tooltip, Legend, Filler,
} from 'chart.js';
import App from './App';
import './index.css';

ChartJS.register(
  CategoryScale, LinearScale, BarElement, ArcElement,
  LineElement, PointElement, Title, Tooltip, Legend, Filler,
);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
