# V7 Tracker Evolution: "Omniscient Engine"

This plan focuses on predictive behavior, sensor fusion, and advanced routing.

## 1. A* / Dijkstra routing over NavGraph (Non-linear extrapolation)
**Problem:** `snapToCorridor` only pulls a straight extrapolation line towards a river.
**Solution:** Transform `nav-graph.ts` into a weighted graph. When the destination (`target_city`) is known, construct a curved path through graph nodes (riverbeds, lowlands) using the A* algorithm.

## 2. Sensor Fusion (Acoustic vs Radar vs Visual)
**Problem:** Acoustic ("heard a moped") and radar observations currently have the same noise weight in the filter.
**Solution:**
- Extract `sensor_type` (`acoustic`, `radar`, `visual`) in `parser_v2.py`.
- Dynamically adjust the measurement noise matrix `R` in `KalmanFilter2D / IMMFilter2D`. Acoustic gets ~5-10 km noise, radar gets hundreds of meters.

## 3. Retrospective Track Smoothing (RTS Smoother)
**Problem:** EKF/IMM only work "forward". Initial noisy data makes the historical track tail zig-zag.
**Solution:** Implement the Rauch-Tung-Striebel (RTS) Smoother. When an MHT branch is confirmed, retrospectively smooth the past coordinates to render a physically realistic tail.

## 4. Swarm Center of Mass Tracking
**Problem:** A swarm of 5 Shaheds can generate chaotic messages, causing track thrashing or incorrect merging.
**Solution:** Implement `SwarmManager`. If multiple targets fly close (< 5 km) with the same vector, group them into a `SwarmCluster`. An observation for one creates "soft gravity" (cross-covariance) for the others.

## 5. 2.5D Kinematics and Terrain Masking
**Problem:** Radars lose targets behind hills. Tracker treats this as `loss`.
**Solution:** Add altitude estimation to `TrackMotionProfile`. If a low-flying UAV enters complex terrain and goes silent, transition it to `terrain_masking` status (increase covariance, but don't kill the track).

## 6. Wind Vector Modeling (Air Speed vs Ground Speed)
**Problem:** A 15 m/s headwind drops a Shahed's ground speed to 120 km/h, which the tracker might flag as an anomaly.
**Solution:** Separate Air Speed and Ground Speed in the EKF state to better model headwinds and prevent false maneuver detections in the IMM.

## 7. Bayesian Target Intent Probability
**Problem:** Straight line extrapolation when target intent is unknown.
**Solution:** Build a probability distribution ("60% Kyiv, 30% Zhytomyr") based on the current vector and `learned_trajectory_targets`. Use the most probable target's gravity to bend the extrapolated path.
