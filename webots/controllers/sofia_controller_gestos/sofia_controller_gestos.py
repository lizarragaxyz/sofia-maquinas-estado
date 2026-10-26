"""Secuencia de gestos de SOFIA - sofia_controller_gestos.

La unidad atiende una cola de comandos; cada comando es un gesto, es decir,
una lista de poses (q1, q2). Estados: ESPERA, MOVER, ASENTAR, SOSTENER.
MOVER lleva el comando hacia la pose con un rate limiter; ASENTAR espera a que
el sensor confirme que las articulaciones llegaron.
"""

from controller import Robot

robot = Robot()
dt_ms = int(robot.getBasicTimeStep())
dt = dt_ms / 1000.0

# Motores: q1, q2. q3 es, mecanicamente, un espejo de q2.
q1 = robot.getDevice('joint_1')
q2 = robot.getDevice('joint_2')
q3 = robot.getDevice('joint_3')

s1 = robot.getDevice('joint_1_sensor')
s2 = robot.getDevice('joint_2_sensor')
s1.enable(dt_ms)
s2.enable(dt_ms)

# Estados
ESPERA = 'ESPERA'
MOVER = 'MOVER'
ASENTAR = 'ASENTAR'
SOSTENER = 'SOSTENER'

# Control (W_MAX de sofia.proto)
W_MAX = 10.471976   # velocidad maxima del motor [rad/s]
V_MAX = 1.5         # velocidad maxima del comando [rad/s]
D_MAX = V_MAX * dt  # variacion maxima del comando por paso [rad]
TOL = 0.01          # tolerancia de llegada [rad]

q1.setVelocity(W_MAX)
q2.setVelocity(W_MAX)
q3.setVelocity(W_MAX)

# Tarea
T_ESPERA = 2.0      # espera entre comandos [s]
T_SOSTENER = 1.0    # tiempo que se sostiene la ultima pose [s]
NEUTRO = (0.0, 0.0)
GESTOS = {          # poses (q1, q2) de cada gesto [rad]
    'si': [(0.0, 0.45), (0.0, -0.25), (0.0, 0.45)],
    'no': [(0.45, 0.0), (-0.45, 0.0), (0.45, 0.0)],
    'ola': [(0.40, 0.0), (0.0, 0.40), (-0.40, 0.0)],
}
comandos = ['si', 'no', 'ola']  # cola de comandos (simulada)


def ruta_gesto(g):
    return list(GESTOS[g])


def ruta_a_neutro():
    return [NEUTRO]


def saturar(u, u_max):
    return max(-u_max, min(u_max, u))


# Comando enviado a los motores (salida del rate limiter)
y1, y2 = NEUTRO


def errores(p1, p2):
    """e_y: falta al comando; e_p: falta al servo [rad]."""
    if not ruta:
        return 0.0, 0.0
    r1, r2 = ruta[0]
    return max(abs(r1 - y1), abs(r2 - y2)), max(abs(r1 - p1), abs(r2 - p2))


# Memoria de la maquina
estado = ESPERA
t_entrada = 0.0     # instante en que se entro al estado actual [s]
gesto = None        # gesto del comando en curso
ruta = []           # poses que faltan por recorrer
al_terminar = None  # estado al que se pasa cuando se acaba la ruta


def cambiar(nuevo, t, p1, p2):
    global estado, t_entrada
    detalle = f'gesto {gesto}' if gesto else 'sin gesto'
    print(f'[{t:6.2f} s] {estado} -> {nuevo}  ({detalle}; q1={p1:+.2f}, q2={p2:+.2f})')
    estado = nuevo
    t_entrada = t
    robot.setCustomData(f'{estado} ({detalle})')    # telemetria


robot.setCustomData(f'{estado} (sin gesto)')
while robot.step(dt_ms) != -1:
    t = robot.getTime()
    p1, p2 = s1.getValue(), s2.getValue()
    t_estado = t - t_entrada

    e_y, e_p = errores(p1, p2)

    # 1) Transiciones
    if estado == ESPERA and t_estado >= T_ESPERA and comandos:
        gesto = comandos.pop(0)
        ruta = ruta_gesto(gesto)
        al_terminar = SOSTENER
        cambiar(MOVER, t, p1, p2)
    elif estado == MOVER and e_y < 1e-6:
        cambiar(ASENTAR, t, p1, p2)
    elif estado == ASENTAR and e_p < TOL:
        ruta.pop(0)
        if not ruta and al_terminar == ESPERA:
            gesto = None
        cambiar(MOVER if ruta else al_terminar, t, p1, p2)
    elif estado == SOSTENER and t_estado >= T_SOSTENER:
        ruta = ruta_a_neutro()
        al_terminar = ESPERA
        cambiar(MOVER, t, p1, p2)

    # 2) Acciones: solo MOVER avanza
    if estado == MOVER:
        r1, r2 = ruta[0]
        y1 += saturar(r1 - y1, D_MAX)
        y2 += saturar(r2 - y2, D_MAX)

    q1.setPosition(y1)
    q2.setPosition(y2)
    q3.setPosition(y2)  # espejo de q2
