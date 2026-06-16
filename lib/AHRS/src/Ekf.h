//=============================================================================================
// Ekf.h
//=============================================================================================
//
// 4-state quaternion Extended Kalman Filter for attitude estimation.
//
// State:        x = [q0 q1 q2 q3]^T  (orientation, sensor frame relative to earth)
// Process:      gyro integration, qdot = 1/2 * Omega(w) * q
// Measurement:  accelerometer measures the earth Z (gravity) direction in body frame,
//               h(q) = [ 2(q1 q3 - q0 q2), 2(q0 q1 + q2 q3), q0^2 - q1^2 - q2^2 + q3^2 ]
//
// Conventions (gyro in rad/s, quaternion form, gravity prediction, Euler angles) match
// the existing Madgwick/Mahony filters so this can be used as a drop-in fusion mode.
//
// NOTE: This filter does not yet estimate gyro bias (a documented future extension); its
// advantage over the complementary filters is covariance-weighted, adaptive correction.
//
//=============================================================================================
#ifndef Ekf_h
#define Ekf_h

#include "helper_3dmath.h"

class Ekf {
  public:
    Ekf();

    // sampleFrequency in Hz; resets the filter state
    void begin(float sampleFrequency);

    // gyro in rad/s, accel in any consistent unit (normalised internally)
    void update(float gx, float gy, float gz, float ax, float ay, float az);

    // process / measurement noise tuning
    void setProcessNoise(float q) { _q = q; }
    void setMeasurementNoise(float r) { _r = r; }

    // parallels the Madgwick/Mahony interface: higher gain => trust accel more (smaller R)
    void setKp(float p) { _r = 1.0f / (1.0f + (p > 0.0f ? p : 0.0f)); }
    void setKi(float i) { (void)i; }

    Quaternion getQuaternion() const { return Quaternion(_x[0], _x[1], _x[2], _x[3]); }
    VectorFloat getEuler() const;

  private:
    void reset();
    void normalizeState();

    float _x[4];      // state quaternion
    float _cov[4][4]; // state covariance (named _cov; _P clashes with newlib ctype macro)
    float _q;        // process noise (per quaternion component)
    float _r;        // measurement noise (per accel axis)
    float _dt;       // sample period
};

#endif
