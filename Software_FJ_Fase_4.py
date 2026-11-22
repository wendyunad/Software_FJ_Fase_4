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
