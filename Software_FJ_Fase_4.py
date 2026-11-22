"""
Sistema Integral de Gestión de Clientes, Servicios y Reservas
Empresa: Software FJ
Curso: Programación 213023 - Fase 4 (Componente Práctico)
Universidad Nacional Abierta y a Distancia (UNAD)
Estudiantes: Cristian Antonio Berrio Herrera
             Wendy Lorena Tarras Palacio
Grupo: 213023_132

Implementa:
- Abstracción, Herencia, Polimorfismo y Encapsulación
- Manejo avanzado de excepciones (personalizadas, try/except/else/finally, chaining)
- Sin bases de datos (listas en memoria + archivo de logs)
- Simulación de más de 10 operaciones (válidas e inválidas)
"""

from abc import ABC, abstractmethod   # Herramientas para crear clases abstractas
from datetime import datetime         # Fecha y hora para reservas y logs
import math                           # Para detectar NaN / infinito en cálculos
import os                             # Ruta absoluta del archivo de log


# ==================== EXCEPCIONES PERSONALIZADAS ====================
class ErrorValidacion(Exception):
    """Excepción base para todos los errores de validación del sistema."""


class ClienteInvalidoError(ErrorValidacion):
    """Se lanza cuando los datos de un cliente no son válidos.
    Puede llevar varios mensajes (uno por cada campo inválido) en 'errores'."""

    def __init__(self, mensaje, errores=None):
        super().__init__(mensaje)
        self.errores = errores if errores else [mensaje]


class ClienteDuplicadoError(ClienteInvalidoError):
    """Se lanza cuando se intenta registrar una identificación ya existente."""


class ServicioNoDisponibleError(ErrorValidacion):
    """Se lanza cuando un servicio no existe, no está disponible o es inválido."""


class ServicioDuplicadoError(ServicioNoDisponibleError):
    """Se lanza cuando se intenta crear un servicio con un nombre ya existente."""


class ReservaInvalidaError(ErrorValidacion):
    """Se lanza cuando una reserva no puede crearse o confirmarse."""


class OperacionNoPermitidaError(ErrorValidacion):
    """Se lanza cuando se intenta una transición de estado no permitida."""


class DatosIncompletosError(ErrorValidacion):
    """Se lanza cuando faltan parámetros obligatorios o son de tipo incorrecto."""


class CalculoInconsistenteError(ErrorValidacion):
    """Se lanza cuando impuestos, descuentos o duración generan un cálculo absurdo."""


# ==================== UTILIDADES ====================
def es_numero(valor):
    """True si es int/float finito (los booleanos NO cuentan como números)."""
    return (isinstance(valor, (int, float)) and not isinstance(valor, bool)
            and math.isfinite(valor))


# ==================== CLASE ABSTRACTA GENERAL ====================
class Entidad(ABC):
    """Clase abstracta que representa entidades generales del sistema."""

    @abstractmethod
    def validar(self):
        """Valida los datos de la entidad (cada subclase define sus reglas)."""

    @abstractmethod
    def obtener_descripcion(self):
        """Retorna una descripción textual de la entidad."""


# ==================== CLASE CLIENTE (ENCAPSULACIÓN) ====================
class Cliente(Entidad):
    """Cliente de Software FJ con atributos privados y validaciones en setters."""

    def __init__(self, nombre, identificacion, telefono="", email=""):
        # Atributos "privados" (convención _): solo se modifican vía propiedades
        self._nombre = None
        self._identificacion = None
        self._telefono = ""
        self._email = ""
        # Al asignar se ejecutan los setters, que validan cada dato.
        # Se validan TODOS los campos y se reúnen los errores (no se corta en el primero).
        errores = []
        for campo, valor in (("nombre", nombre), ("identificacion", identificacion),
                             ("telefono", telefono), ("email", email)):
            try:
                setattr(self, campo, valor)
            except ClienteInvalidoError as e:
                errores.append(f"[{campo}] {e}")
        if errores:
            raise ClienteInvalidoError(" | ".join(errores), errores)
        self.validar()  # Validación final de obligatorios

    @property
    def nombre(self):
        return self._nombre

    @nombre.setter
    def nombre(self, valor):
        # Debe ser texto con al menos 3 caracteres útiles
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ClienteInvalidoError("El nombre debe tener al menos 3 caracteres.")
        self._nombre = valor.strip()

    @property
    def identificacion(self):
        return self._identificacion

    @identificacion.setter
    def identificacion(self, valor):
        # Solo dígitos ASCII y mínimo 6
        texto = str(valor).strip() if valor is not None else ""
        if not (texto.isascii() and texto.isdigit()) or len(texto) < 6:
            raise ClienteInvalidoError(
                "La identificación debe ser numérica y tener al menos 6 dígitos.")
        self._identificacion = texto

    @property
    def telefono(self):
        return self._telefono

    @telefono.setter
    def telefono(self, valor):
        # El teléfono es opcional; si se da, debe ser numérico de 7+ dígitos
        texto = str(valor).strip() if valor else ""
        if texto and (not (texto.isascii() and texto.isdigit()) or len(texto) < 7):
            raise ClienteInvalidoError(
                "El teléfono debe contener solo números y tener al menos 7 dígitos.")
        self._telefono = texto

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, valor):
        # El email es opcional; si se da, debe tener formato usuario@dominio.ext
        texto = str(valor).strip() if valor else ""
        if texto:
            usuario, arroba, dominio = texto.partition("@")
            if (not arroba or not usuario or "@" in dominio or " " in texto
                    or "." not in dominio or dominio.startswith(".")
                    or dominio.endswith(".") or ".." in dominio):
                raise ClienteInvalidoError("El email no tiene un formato válido.")
        self._email = texto

    def validar(self):
        # Regla del negocio: nombre e identificación son obligatorios
        if not self._nombre or not self._identificacion:
            raise DatosIncompletosError("Nombre e identificación son obligatorios.")

    def obtener_descripcion(self):
        return f"Cliente: {self.nombre} | ID: {self.identificacion}"


# ==================== CLASE ABSTRACTA SERVICIO ====================
class Servicio(Entidad):
    """Clase abstracta de la que heredan todos los servicios de Software FJ."""

    DURACION_MAXIMA = 24      # Cada servicio sobrescribe su propio límite

    def __init__(self, nombre, precio_base, disponible=True):
        # El nombre es obligatorio y debe ser texto
        if nombre is None or not str(nombre).strip():
            raise DatosIncompletosError("El nombre del servicio es obligatorio.")
        if not isinstance(disponible, bool):
            raise DatosIncompletosError("'disponible' debe ser True o False.")
        self.nombre = str(nombre).strip()
        # Conversión segura del precio: se encadena la excepción original (chaining)
        try:
            if isinstance(precio_base, bool):
                raise TypeError("un booleano no es un precio")
            self.precio_base = float(precio_base)
            if not math.isfinite(self.precio_base):
                raise ValueError("valor no finito")
        except (TypeError, ValueError) as e:
            raise ServicioNoDisponibleError(
                f"El precio '{precio_base}' no es un número válido.") from e
        self.disponible = disponible

    # ---- Métodos abstractos (cada servicio los sobrescribe) ----
    @abstractmethod
    def calcular_costo(self, duracion=1, impuesto=0.19, descuento=0.0):
        """Calcula el costo total de forma polimórfica."""

    @abstractmethod
    def describir_servicio(self):
        """Descripción propia de cada servicio (polimorfismo)."""

    @abstractmethod
    def validar_duracion(self, duracion):
        """Valida la duración según las reglas propias de cada servicio."""

    # ---- Métodos sobrecargados (variantes del cálculo de costos) ----
    def cotizar(self, *args, **kwargs):
        """Sobrecarga simulada del cálculo de costos. Variantes admitidas:
            cotizar(duracion)
            cotizar(duracion, impuesto)
            cotizar(duracion, impuesto, descuento)
            cotizar(duracion, descuento=10)  /  cotizar(duracion=2, impuesto=0.0)
        """
        nombres = ("duracion", "impuesto", "descuento")
        if not args and not kwargs:
            raise DatosIncompletosError("cotizar() requiere al menos la duración.")
        if len(args) > len(nombres):
            raise DatosIncompletosError("cotizar() admite máximo 3 parámetros.")
        parametros = dict(zip(nombres, args))
        for clave, valor in kwargs.items():
            if clave not in nombres:
                raise DatosIncompletosError(f"Parámetro desconocido: '{clave}'.")
            if clave in parametros:
                raise DatosIncompletosError(f"Parámetro repetido: '{clave}'.")
            parametros[clave] = valor
        if "duracion" not in parametros:
            raise DatosIncompletosError("La duración es obligatoria.")
        return self.calcular_costo(**parametros)

    # ---- Reglas comunes ----
    def validar(self):
        if self.precio_base <= 0:
            raise ServicioNoDisponibleError(
                f"El precio del servicio '{self.nombre}' debe ser mayor a cero.")
        if not self.disponible:
            raise ServicioNoDisponibleError(
                f"El servicio '{self.nombre}' no está disponible.")

    def obtener_descripcion(self):
        return self.describir_servicio()

    def _calcular(self, duracion, impuesto, descuento, recargo=0.0):
        """Fórmula común: valida parámetros y calcula el total.
        impuesto es fracción (0.19 = 19%); descuento y recargo son porcentajes."""
        self.validar()
        if not es_numero(duracion) or duracion <= 0:
            raise ReservaInvalidaError("La duración debe ser un número mayor a cero.")
        self.validar_duracion(duracion)                     # Regla propia del servicio
        if not es_numero(impuesto) or not 0 <= impuesto <= 1:
            raise CalculoInconsistenteError("El impuesto debe estar entre 0 y 1 (ej. 0.19).")
        if not es_numero(descuento) or not 0 <= descuento <= 100:
            raise CalculoInconsistenteError("El descuento debe estar entre 0 y 100 (%).")
        subtotal = self.precio_base * duracion
        subtotal *= (1 + recargo / 100)            # Recargo propio del servicio
        con_descuento = subtotal * (1 - descuento / 100)
        total = round(con_descuento * (1 + impuesto), 2)
        if total <= 0:
            raise CalculoInconsistenteError("El cálculo produjo un costo no positivo.")
        return total


# ==================== SERVICIOS ESPECIALIZADOS ====================
class ReservaSala(Servicio):
    """Reserva de salas (precio por hora). 5% extra de descuento desde 8 horas."""

    DURACION_MAXIMA = 12

    def calcular_costo(self, duracion=1, impuesto=0.19, descuento=0.0):
        if es_numero(duracion) and es_numero(descuento) and duracion >= 8:
            descuento = min(100, descuento + 5)    # Beneficio por jornada larga
        return self._calcular(duracion, impuesto, descuento)

    def validar_duracion(self, duracion):
        if duracion > self.DURACION_MAXIMA:
            raise ReservaInvalidaError(
                f"Una sala no se puede reservar por más de {self.DURACION_MAXIMA} horas.")

    def describir_servicio(self):
        return (f"Reserva de Sala '{self.nombre}' | Precio/hora: ${self.precio_base:.2f} "
                f"| Disponible: {self.disponible}")


class AlquilerEquipo(Servicio):
    """Alquiler de equipos (precio por día). Incluye 5% de recargo por seguro."""

    DURACION_MAXIMA = 30

    def calcular_costo(self, duracion=1, impuesto=0.19, descuento=0.0):
        return self._calcular(duracion, impuesto, descuento, recargo=5.0)

    def validar_duracion(self, duracion):
        if duracion != int(duracion):
            raise ReservaInvalidaError("Los equipos se alquilan por días completos.")
        if duracion > self.DURACION_MAXIMA:
            raise ReservaInvalidaError(
                f"Un equipo no se puede alquilar por más de {self.DURACION_MAXIMA} días.")

    def describir_servicio(self):
        return (f"Alquiler de Equipo '{self.nombre}' | Precio/día: ${self.precio_base:.2f} "
                f"| Disponible: {self.disponible}")


class AsesoriaEspecializada(Servicio):
    """Asesoría especializada (precio por hora). Sin recargos ni beneficios."""

    DURACION_MAXIMA = 8

    def calcular_costo(self, duracion=1, impuesto=0.19, descuento=0.0):
        return self._calcular(duracion, impuesto, descuento)

    def validar_duracion(self, duracion):
        if duracion > self.DURACION_MAXIMA:
            raise ReservaInvalidaError(
                f"Una asesoría no puede durar más de {self.DURACION_MAXIMA} horas.")

    def describir_servicio(self):
        return (f"Asesoría Especializada '{self.nombre}' | Precio/hora: ${self.precio_base:.2f} "
                f"| Disponible: {self.disponible}")


# ==================== CLASE RESERVA ====================
class Reserva(Entidad):
    """Integra cliente, servicio, duración y estado (Pendiente→Confirmada→Procesada/Cancelada)."""

    def __init__(self, cliente, servicio, duracion, estado="Pendiente"):
        self.cliente = cliente
        self.servicio = servicio
        self.duracion = duracion
        self.estado = estado
        self.costo = 0.0
        self.fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.validar()

    def validar(self):
        if not isinstance(self.cliente, Cliente):
            raise ReservaInvalidaError("La reserva requiere un cliente válido.")
        if not isinstance(self.servicio, Servicio):
            raise ReservaInvalidaError("La reserva requiere un servicio válido.")
        if not es_numero(self.duracion) or self.duracion <= 0:
            raise ReservaInvalidaError("La duración debe ser un número mayor a cero.")

    def obtener_descripcion(self):
        return (f"{self.cliente.nombre} | {self.servicio.nombre} | {self.duracion} | "
                f"${self.costo:.2f} | {self.estado}")

    def confirmar(self, impuesto=0.19, descuento=0.0):
        """Calcula el costo y confirma. Encadena cualquier error con 'from e'."""
        if self.estado != "Pendiente":
            raise OperacionNoPermitidaError(
                f"No se puede confirmar una reserva en estado '{self.estado}'.")
        try:
            costo = self.servicio.calcular_costo(self.duracion, impuesto, descuento)
        except Exception as e:
            raise ReservaInvalidaError(f"No se pudo confirmar la reserva: {e}") from e
        else:
            self.costo = costo
            self.estado = "Confirmada"   # Solo si no hubo error
            return True

    def cancelar(self):
        """Cancela la reserva si aún no está cancelada ni procesada."""
        if self.estado == "Cancelada":
            raise OperacionNoPermitidaError("La reserva ya está cancelada.")
        if self.estado == "Procesada":
            raise OperacionNoPermitidaError("No se puede cancelar una reserva ya procesada.")
        self.estado = "Cancelada"
        return True

    def procesar(self):
        """Procesa la reserva (solo si está confirmada)."""
        if self.estado != "Confirmada":
            raise OperacionNoPermitidaError(
                f"Solo se pueden procesar reservas confirmadas (estado actual: {self.estado}).")
        self.estado = "Procesada"
        return True
      
# ==================== SISTEMA PRINCIPAL ====================
class SistemaSoftwareFJ:
    """Gestiona clientes, servicios y reservas en listas y registra todo en un log."""

    TIPOS_SERVICIO = {"sala": ReservaSala, "equipo": AlquilerEquipo,
                      "asesoria": AsesoriaEspecializada, "asesoría": AsesoriaEspecializada}

    def __init__(self, log_file=None):
        self.clientes = []     # Lista interna de clientes
        self.servicios = []    # Lista interna de servicios
        self.reservas = []     # Lista interna de reservas
        # El log se guarda junto al script, sin importar desde dónde se ejecute
        if log_file is None:
            log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "logs_software_fj.txt")
        self.log_file = log_file
        self._inicializar_log()

    def _inicializar_log(self):
        # Marca el inicio de cada sesión en el archivo de logs
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"\n=== INICIO DE SESIÓN: {datetime.now()} ===\n")
        except OSError as e:
            print(f"(No se pudo inicializar el log: {e})")

    def registrar_evento(self, mensaje, es_error=False):
        """Escribe en el log y en pantalla. Nunca debe detener el programa."""
        tipo = "ERROR" if es_error else "EVENTO"
        linea = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{tipo}] {mensaje}\n"
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(linea)
        except OSError as e:
            print(f"(No se pudo escribir en el log: {e})")
        print(linea.strip())

    def _registrar_fallo(self, contexto, error):
        """Registra el error y, si existe, la causa original (encadenamiento)."""
        if isinstance(error, ClienteInvalidoError) and len(error.errores) > 1:
            self.registrar_evento(f"{contexto}: {len(error.errores)} errores de validación",
                                  es_error=True)
            for detalle in error.errores:
                self.registrar_evento(f"   - {detalle}", es_error=True)
            return
        mensaje = f"{contexto}: {type(error).__name__}: {error}"
        if error.__cause__ is not None:
            mensaje += f" | Causa: {type(error.__cause__).__name__}: {error.__cause__}"
        self.registrar_evento(mensaje, es_error=True)

    # ---------- Clientes ----------
    def registrar_cliente(self, nombre, identificacion, telefono="", email=""):
        try:
            cliente = Cliente(nombre, identificacion, telefono, email)
            # Evita identificaciones repetidas
            if any(c.identificacion == cliente.identificacion for c in self.clientes):
                raise ClienteDuplicadoError(
                    f"Ya existe un cliente con la identificación {cliente.identificacion}.")
        except Exception as e:
            self._registrar_fallo("Fallo al registrar cliente", e)
            raise
        else:
            self.clientes.append(cliente)
            self.registrar_evento(f"Cliente registrado: {cliente.obtener_descripcion()}")
            return cliente
        finally:
            self.registrar_evento("Fin de operación: registrar_cliente")

    # ---------- Servicios ----------
    def crear_servicio(self, tipo, nombre, precio, disponible=True):
        try:
            clase = self.TIPOS_SERVICIO.get(str(tipo).lower().strip())
            if clase is None:
                raise ServicioNoDisponibleError(f"Tipo de servicio no reconocido: '{tipo}'.")
            servicio = clase(nombre, precio, disponible)   # Polimorfismo: misma interfaz
            servicio.validar()
            if any(s.nombre.lower() == servicio.nombre.lower() for s in self.servicios):
                raise ServicioDuplicadoError(
                    f"Ya existe un servicio llamado '{servicio.nombre}'.")
        except Exception as e:
            self._registrar_fallo("Fallo al crear servicio", e)
            raise
        else:
            self.servicios.append(servicio)
            self.registrar_evento(f"Servicio creado: {servicio.describir_servicio()}")
            return servicio
        finally:
            self.registrar_evento("Fin de operación: crear_servicio")

    # ---------- Reservas ----------
    def crear_reserva(self, id_cliente, nombre_servicio, duracion, impuesto=0.19, descuento=0.0):
        try:
            cliente = next((c for c in self.clientes
                            if c.identificacion == str(id_cliente).strip()), None)
            if not cliente:
                raise ReservaInvalidaError("Cliente no encontrado.")
            servicio = next((s for s in self.servicios
                             if s.nombre.lower() == str(nombre_servicio).strip().lower()), None)
            if not servicio:
                raise ServicioNoDisponibleError("Servicio no encontrado.")
            reserva = Reserva(cliente, servicio, duracion)
            reserva.confirmar(impuesto, descuento)
        except Exception as e:
            self._registrar_fallo("Fallo al crear reserva", e)
            raise
        else:
            self.reservas.append(reserva)
            self.registrar_evento(
                f"Reserva #{len(self.reservas)} confirmada: {cliente.nombre} → "
                f"{servicio.nombre} | Costo: ${reserva.costo:.2f}")
            return reserva
        finally:
            self.registrar_evento("Fin de operación: crear_reserva")

    def _obtener_reserva(self, numero):
        """Busca una reserva por su número (1, 2, 3...)."""
        try:
            indice = int(numero) - 1
            if indice < 0:
                raise IndexError("índice negativo")
            return self.reservas[indice]
        except (ValueError, TypeError, IndexError) as e:
            raise ReservaInvalidaError(f"La reserva #{numero} no existe.") from e

    def cancelar_reserva(self, numero):
        try:
            reserva = self._obtener_reserva(numero)
            reserva.cancelar()
        except Exception as e:
            self._registrar_fallo(f"Fallo al cancelar reserva #{numero}", e)
            raise
        else:
            self.registrar_evento(f"Reserva #{numero} cancelada.")
            return reserva
        finally:
            self.registrar_evento("Fin de operación: cancelar_reserva")

    def procesar_reserva(self, numero):
        try:
            reserva = self._obtener_reserva(numero)
            reserva.procesar()
        except Exception as e:
            self._registrar_fallo(f"Fallo al procesar reserva #{numero}", e)
            raise
        else:
            self.registrar_evento(f"Reserva #{numero} procesada.")
            return reserva
        finally:
            self.registrar_evento("Fin de operación: procesar_reserva")

    def listar_todo(self):
        print("\n=== CLIENTES ===")
        for c in self.clientes:
            print(c.obtener_descripcion())
        print("\n=== SERVICIOS ===")
        for s in self.servicios:
            print(s.describir_servicio())   # Polimorfismo en acción
        print("\n=== RESERVAS ===")
        for i, r in enumerate(self.reservas, 1):
            print(f"#{i} | {r.obtener_descripcion()}")


# ==================== SIMULACIÓN DE OPERACIONES ====================
def ejecutar_simulacion():
    """Ejecuta operaciones válidas e inválidas; el programa nunca se detiene."""
    sistema = SistemaSoftwareFJ()
    print("=== SIMULACIÓN DE OPERACIONES (válidas e inválidas) ===\n")

    operaciones = [
        ("Cliente válido", lambda: sistema.registrar_cliente("Ana Gómez", "1023456789", "3001234567", "ana@email.com")),
        ("Cliente válido (segundo)", lambda: sistema.registrar_cliente("Luis Pérez", "52345678")),
        ("Cliente inválido (nombre corto)", lambda: sistema.registrar_cliente("Jo", "123456")),
        ("Cliente inválido (ID no numérico)", lambda: sistema.registrar_cliente("Carlos Ruiz", "ABC123")),
        ("Cliente inválido (ID duplicado)", lambda: sistema.registrar_cliente("Ana Duplicada", "1023456789")),
        ("Cliente inválido (email mal formado)", lambda: sistema.registrar_cliente("María López", "70123456", "", "maria@@correo")),
        ("Cliente inválido (todos los campos mal)", lambda: sistema.registrar_cliente("wendy", "uno dos", "5", "jdfhgds")),
        ("Servicio Sala válido", lambda: sistema.crear_servicio("sala", "Sala Ejecutiva", 80.0)),
        ("Servicio Equipo válido", lambda: sistema.crear_servicio("equipo", "Laptop Gaming", 45.0)),
        ("Servicio Asesoría válida", lambda: sistema.crear_servicio("asesoria", "Consultoría Python", 120.0)),
        ("Servicio inválido (precio 0)", lambda: sistema.crear_servicio("sala", "Sala Pequeña", 0)),
        ("Servicio inválido (precio no numérico)", lambda: sistema.crear_servicio("sala", "Sala Rara", "abc")),
        ("Servicio inválido (tipo desconocido)", lambda: sistema.crear_servicio("catering", "Café", 10)),
        ("Servicio inválido (nombre duplicado)", lambda: sistema.crear_servicio("sala", "Sala Ejecutiva", 90)),
        ("Servicio no disponible", lambda: sistema.crear_servicio("equipo", "Proyector", 30.0, disponible=False)),
        ("Reserva exitosa (con descuento)", lambda: sistema.crear_reserva("1023456789", "Sala Ejecutiva", 3, descuento=10)),
        ("Reserva con cliente inexistente", lambda: sistema.crear_reserva("999999", "Laptop Gaming", 2)),
        ("Reserva con servicio inexistente", lambda: sistema.crear_reserva("1023456789", "Servicio Fantasma", 1)),
        ("Reserva con duración inválida (0)", lambda: sistema.crear_reserva("1023456789", "Consultoría Python", 0)),
        ("Reserva con duración excesiva (asesoría 20h)", lambda: sistema.crear_reserva("1023456789", "Consultoría Python", 20)),
        ("Reserva con descuento inconsistente", lambda: sistema.crear_reserva("52345678", "Laptop Gaming", 2, descuento=150)),
        ("Reserva con duración de tipo incorrecto", lambda: sistema.crear_reserva("52345678", "Laptop Gaming", "dos")),
        ("Cancelar reserva #1", lambda: sistema.cancelar_reserva(1)),
        ("Cancelar reserva #1 otra vez (inválido)", lambda: sistema.cancelar_reserva(1)),
        ("Procesar reserva cancelada (inválido)", lambda: sistema.procesar_reserva(1)),
        ("Reserva exitosa de asesoría", lambda: sistema.crear_reserva("52345678", "Consultoría Python", 2)),
        ("Procesar reserva #2", lambda: sistema.procesar_reserva(2)),
        ("Procesar reserva inexistente (#99)", lambda: sistema.procesar_reserva(99)),
        ("Cotización sobrecargada (3 variantes)", lambda: (
            print("  cotizar(2)            ->", sistema.servicios[1].cotizar(2)),
            print("  cotizar(2, 0.0)       ->", sistema.servicios[1].cotizar(2, 0.0)),
            print("  cotizar(2, 0.19, 10)  ->", sistema.servicios[1].cotizar(2, 0.19, 10)),
            sistema.servicios[1].cotizar())),    # Sin parámetros: error controlado
    ]

    for i, (descripcion, operacion) in enumerate(operaciones, 1):
        print(f"\n--- Operación {i}: {descripcion} ---")
        try:
            operacion()
        except Exception as e:
            if isinstance(e, ClienteInvalidoError) and len(e.errores) > 1:
                print(f"✗ Error controlado: {type(e).__name__} ({len(e.errores)} errores)")
                for detalle in e.errores:
                    print(f"    ✗ {detalle}")
            else:
                print(f"✗ Error controlado: {type(e).__name__}: {e}")
            if e.__cause__:   # Muestra el encadenamiento de excepciones
                print(f"  ↳ Causa original: {type(e.__cause__).__name__}: {e.__cause__}")
        else:
            print("✓ Éxito → bloque else: operación completada sin errores.")
        finally:
            print("→ Bloque finally: operación finalizada.")

    print("\n" + "=" * 50)
    sistema.listar_todo()
    print(f"\nLogs guardados en: {os.path.abspath(sistema.log_file)}")


# ==================== MENÚ INTERACTIVO ====================
def leer_numero(texto, etiqueta):
    """Convierte texto a número encadenando el error original."""
    try:
        return float(texto.replace(",", "."))
    except ValueError as e:
        raise DatosIncompletosError(f"{etiqueta} debe ser un valor numérico.") from e


def menu_principal():
    sistema = SistemaSoftwareFJ()
    while True:
        print("\n" + "=" * 50)
        print("   SISTEMA SOFTWARE FJ - Gestión de Clientes y Reservas")
        print("=" * 50)
        print("1. Registrar Cliente")
        print("2. Crear Servicio")
        print("3. Crear Reserva")
        print("4. Cancelar Reserva")
        print("5. Procesar Reserva")
        print("6. Listar Todo")
        print("7. Ejecutar Simulación Completa")
        print("0. Salir")
        try:
            opcion = input("\nSeleccione una opción: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEntrada finalizada. Saliendo del sistema...")
            break

        try:
            if opcion == "1":
                datos = (input("Nombre: "), input("Identificación: "),
                         input("Teléfono (opcional): "), input("Email (opcional): "))
                try:
                    cliente = sistema.registrar_cliente(*datos)
                except ErrorValidacion as e:
                    # Mensaje claro en la interfaz: el cliente NO quedó registrado
                    print("\n" + "!" * 50)
                    print("✗ NO SE PUDO REGISTRAR EL CLIENTE")
                    print("!" * 50)
                    if isinstance(e, ClienteInvalidoError) and len(e.errores) > 1:
                        print("Motivos del error:")
                        for detalle in e.errores:
                            print(f"  ✗ {detalle}")
                    else:
                        print(f"Motivo del error: {e}")
                    print("Por favor, verifique los datos e intente de nuevo.")
                else:
                    print("\n" + "=" * 50)
                    print(f"✓ CLIENTE REGISTRADO CORRECTAMENTE: {cliente.obtener_descripcion()}")
                    print("=" * 50)
            elif opcion == "2":
                tipo = input("Tipo (sala/equipo/asesoria): ")
                nombre = input("Nombre del servicio: ")
                sistema.crear_servicio(tipo, nombre, input("Precio base: "))
            elif opcion == "3":
                id_c = input("Identificación del cliente: ")
                nom_s = input("Nombre del servicio: ")
                duracion = leer_numero(input("Duración: "), "La duración")
                sistema.crear_reserva(id_c, nom_s, duracion)
            elif opcion == "4":
                sistema.cancelar_reserva(input("Número de reserva: "))
            elif opcion == "5":
                sistema.procesar_reserva(input("Número de reserva: "))
            elif opcion == "6":
                sistema.listar_todo()
            elif opcion == "7":
                ejecutar_simulacion()
            elif opcion == "0":
                print("Saliendo del sistema...")
                break
            else:
                print("Opción no válida.")
        except (EOFError, KeyboardInterrupt):
            print("\nEntrada finalizada. Saliendo del sistema...")
            break
        except ErrorValidacion as e:
            # Ya quedó registrado en el log por el sistema (salvo errores de captura)
            if isinstance(e, ClienteInvalidoError) and len(e.errores) > 1:
                print("Error controlado: corrija los siguientes campos:")
                for detalle in e.errores:
                    print(f"  ✗ {detalle}")
            else:
                print(f"Error controlado en el menú: {e}")
            if e.__cause__ and isinstance(e, DatosIncompletosError):
                sistema.registrar_evento(f"Entrada inválida en el menú: {e}", es_error=True)
        except Exception as e:   # Última red de seguridad: el menú nunca se cae
            sistema.registrar_evento(f"Error inesperado en el menú: {type(e).__name__}: {e}",
                                     es_error=True)
            print(f"Error inesperado (el sistema continúa): {e}")


if __name__ == "__main__":
    print("Iniciando Sistema Software FJ...")
    ejecutar_simulacion()   # Demostración automática (válidas e inválidas)
    menu_principal()        # Luego queda disponible el menú interactivo

