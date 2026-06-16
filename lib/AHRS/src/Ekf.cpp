//=============================================================================================
// Ekf.cpp
//=============================================================================================
#include "Ekf.h"
#include <cmath>

Ekf::Ekf(): _q(1e-4f), _r(1e-1f), _dt(1.0f / 1000.0f)
{
  reset();
}

void Ekf::reset()
{
  _x[0] = 1.0f; _x[1] = 0.0f; _x[2] = 0.0f; _x[3] = 0.0f;
  for(int i = 0; i < 4; i++)
  {
    for(int j = 0; j < 4; j++)
    {
      _cov[i][j] = (i == j) ? 1.0f : 0.0f;
    }
  }
}

void Ekf::begin(float sampleFrequency)
{
  _dt = (sampleFrequency > 0.0f) ? (1.0f / sampleFrequency) : (1.0f / 1000.0f);
  reset();
}

void Ekf::normalizeState()
{
  float n = _x[0] * _x[0] + _x[1] * _x[1] + _x[2] * _x[2] + _x[3] * _x[3];
  if(!std::isfinite(n) || n < 1e-12f)
  {
    // degenerate state: recover to identity to stop NaN/Inf propagation
    _x[0] = 1.0f; _x[1] = 0.0f; _x[2] = 0.0f; _x[3] = 0.0f;
    return;
  }
  float inv = 1.0f / sqrtf(n);
  _x[0] *= inv; _x[1] *= inv; _x[2] *= inv; _x[3] *= inv;
}

// Inverse of a symmetric positive-definite 3x3 matrix via cofactors.
// Returns false if the matrix is singular / non-finite.
static bool invert3x3(const float m[3][3], float out[3][3])
{
  const float a = m[0][0], b = m[0][1], c = m[0][2];
  const float d = m[1][0], e = m[1][1], f = m[1][2];
  const float g = m[2][0], h = m[2][1], i = m[2][2];

  const float A =  (e * i - f * h);
  const float B = -(d * i - f * g);
  const float C =  (d * h - e * g);
  const float det = a * A + b * B + c * C;

  if(!std::isfinite(det) || std::fabs(det) < 1e-12f) return false;
  const float invDet = 1.0f / det;

  out[0][0] = A * invDet;
  out[0][1] = (c * h - b * i) * invDet;
  out[0][2] = (b * f - c * e) * invDet;
  out[1][0] = B * invDet;
  out[1][1] = (a * i - c * g) * invDet;
  out[1][2] = (c * d - a * f) * invDet;
  out[2][0] = C * invDet;
  out[2][1] = (b * g - a * h) * invDet;
  out[2][2] = (a * e - b * d) * invDet;
  return true;
}

void Ekf::update(float gx, float gy, float gz, float ax, float ay, float az)
{
  const float q0 = _x[0], q1 = _x[1], q2 = _x[2], q3 = _x[3];
  const float hdt = 0.5f * _dt;

  // ---- Predict ----
  // State transition F = I + 0.5*dt*Omega(w), with qdot = 0.5*Omega*q
  float F[4][4] = {
    { 1.0f,     -hdt * gx, -hdt * gy, -hdt * gz },
    { hdt * gx,  1.0f,      hdt * gz, -hdt * gy },
    { hdt * gy, -hdt * gz,  1.0f,      hdt * gx },
    { hdt * gz,  hdt * gy, -hdt * gx,  1.0f     },
  };

  // x_pred = F * x
  float xp[4];
  for(int r = 0; r < 4; r++)
  {
    xp[r] = F[r][0] * q0 + F[r][1] * q1 + F[r][2] * q2 + F[r][3] * q3;
  }
  _x[0] = xp[0]; _x[1] = xp[1]; _x[2] = xp[2]; _x[3] = xp[3];
  normalizeState();

  // P = F*P*F^T + Q
  float FP[4][4];
  for(int r = 0; r < 4; r++)
    for(int c = 0; c < 4; c++)
    {
      float s = 0.0f;
      for(int k = 0; k < 4; k++) s += F[r][k] * _cov[k][c];
      FP[r][c] = s;
    }
  for(int r = 0; r < 4; r++)
    for(int c = 0; c < 4; c++)
    {
      float s = 0.0f;
      for(int k = 0; k < 4; k++) s += FP[r][k] * F[c][k]; // * F^T
      _cov[r][c] = s + ((r == c) ? _q : 0.0f);
    }

  // ---- Measurement update (accelerometer = gravity direction) ----
  float norm = sqrtf(ax * ax + ay * ay + az * az);
  if(!std::isfinite(norm) || norm < 1e-6f) return; // no usable accel this step
  ax /= norm; ay /= norm; az /= norm;

  const float p0 = _x[0], p1 = _x[1], p2 = _x[2], p3 = _x[3];

  // predicted gravity direction h(q)
  const float h0 = 2.0f * (p1 * p3 - p0 * p2);
  const float h1 = 2.0f * (p0 * p1 + p2 * p3);
  const float h2 = p0 * p0 - p1 * p1 - p2 * p2 + p3 * p3;

  // innovation y = z - h
  const float y0 = ax - h0;
  const float y1 = ay - h1;
  const float y2 = az - h2;

  // measurement Jacobian H = dh/dq (3x4)
  const float H[3][4] = {
    { -2.0f * p2,  2.0f * p3, -2.0f * p0,  2.0f * p1 },
    {  2.0f * p1,  2.0f * p0,  2.0f * p3,  2.0f * p2 },
    {  2.0f * p0, -2.0f * p1, -2.0f * p2,  2.0f * p3 },
  };

  // S = H*P*H^T + R   (3x3)
  float HP[3][4];
  for(int r = 0; r < 3; r++)
    for(int c = 0; c < 4; c++)
    {
      float s = 0.0f;
      for(int k = 0; k < 4; k++) s += H[r][k] * _cov[k][c];
      HP[r][c] = s;
    }
  float S[3][3];
  for(int r = 0; r < 3; r++)
    for(int c = 0; c < 3; c++)
    {
      float s = 0.0f;
      for(int k = 0; k < 4; k++) s += HP[r][k] * H[c][k]; // * H^T
      S[r][c] = s + ((r == c) ? _r : 0.0f);
    }

  float Sinv[3][3];
  if(!invert3x3(S, Sinv)) return; // skip correction if innovation covariance is singular

  // K = P*H^T*Sinv   (4x3)
  float PHt[4][3];
  for(int r = 0; r < 4; r++)
    for(int c = 0; c < 3; c++)
    {
      float s = 0.0f;
      for(int k = 0; k < 4; k++) s += _cov[r][k] * H[c][k]; // H^T column
      PHt[r][c] = s;
    }
  float K[4][3];
  for(int r = 0; r < 4; r++)
    for(int c = 0; c < 3; c++)
    {
      float s = 0.0f;
      for(int k = 0; k < 3; k++) s += PHt[r][k] * Sinv[k][c];
      K[r][c] = s;
    }

  // x = x + K*y
  _x[0] += K[0][0] * y0 + K[0][1] * y1 + K[0][2] * y2;
  _x[1] += K[1][0] * y0 + K[1][1] * y1 + K[1][2] * y2;
  _x[2] += K[2][0] * y0 + K[2][1] * y1 + K[2][2] * y2;
  _x[3] += K[3][0] * y0 + K[3][1] * y1 + K[3][2] * y2;
  normalizeState();

  // P = (I - K*H) * P
  float KH[4][4];
  for(int r = 0; r < 4; r++)
    for(int c = 0; c < 4; c++)
    {
      float s = 0.0f;
      for(int k = 0; k < 3; k++) s += K[r][k] * H[k][c];
      KH[r][c] = ((r == c) ? 1.0f : 0.0f) - s;
    }
  float Pnew[4][4];
  for(int r = 0; r < 4; r++)
    for(int c = 0; c < 4; c++)
    {
      float s = 0.0f;
      for(int k = 0; k < 4; k++) s += KH[r][k] * _cov[k][c];
      Pnew[r][c] = s;
    }
  for(int r = 0; r < 4; r++)
    for(int c = 0; c < 4; c++) _cov[r][c] = Pnew[r][c];
}

VectorFloat Ekf::getEuler() const
{
  const float q0 = _x[0], q1 = _x[1], q2 = _x[2], q3 = _x[3];
  // matches Madgwick::computeAngles convention
  const float roll  = atan2f(q0 * q1 + q2 * q3, 0.5f - q1 * q1 - q2 * q2);
  const float pitch = asinf(-2.0f * (q1 * q3 - q0 * q2));
  const float yaw   = atan2f(q1 * q2 + q0 * q3, 0.5f - q2 * q2 - q3 * q3);
  return VectorFloat(roll, pitch, yaw);
}
