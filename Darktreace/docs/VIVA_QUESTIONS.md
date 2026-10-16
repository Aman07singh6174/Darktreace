# DarkTrace Viva Questions and Answers

1. **What is DarkTrace?**  
   A local demo of defensive security monitoring and Admin response.

2. **Does it access the real dark web?**  
   No. All identities and events are fictional and stay in the local MySQL database.

3. **Which technologies are used?**  
   Python, Flask, SQLAlchemy, MySQL, HTML, CSS, JavaScript, Chart.js, and Three.js.

4. **Who can log in?**  
   Only the single Admin configured in the local `.env` file. Monitored identities cannot sign in.

5. **How is the Admin password stored?**  
   The app stores a Werkzeug password hash, not the original password.

6. **What does the demo seed script create?**  
   Fictional users, communities, posts, threat reports, security logs, login attempts, alerts, and audit actions.

7. **How does risk scoring work?**  
   Rule-based events add bounded points, then scores are classified Low, Medium, High, or Critical.

8. **What happens when a user crosses the risk threshold?**  
   The monitored record is marked suspicious, temporarily blocked, logged, and shown in an Admin alert.

9. **Does temporary blocking block an IP address?**  
   No. It changes only a fictional account's local demo access state.

10. **How does a block expire?**  
    MySQL stores its start and expiry times; the app clears expired blocks on later requests and records the restoration.

11. **What does the relationship graph show?**  
    Links among fictional users, communities, posts, and threat reports.

12. **What is one important limitation?**  
    The detector uses simple rules and can miss context or flag harmless demo text.