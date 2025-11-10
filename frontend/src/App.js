import logo from './logo.svg';
import img1 from './images/wkulogo.png';
import img2 from './images/campus.png';
import './App.css';
import './index.css';

function handleClick() {
  alert('오른쪽 버튼 클릭!');
}
function App() {
  return (
    <div className="App">
      <div className="bar">
        <div className="left-section">
        <img className="img1" alt="" src={img1}/>
        <span className="home">Home</span>
      </div>
      <div className="right-section">
        <button className="signup-btn" onClick={() => alert('SIGN UP 클릭!')}>SIGN UP</button>
        <button className="login-btn" onClick={() => alert('LOGIN 클릭!')}>LOG IN</button>
        </div>
    </div>
    <img className="img2" alt="" src={img2}/> 
    <div className="box">
      
    </div>
    <footer className="bar1"> 
    </footer>
</div>
  );
}

export default App;

