"""
Sistema Integral de Gestión de Clientes, Servicios y Reservas
Empresa: Software FJ
Curso: Programación 213023 - Fase 4 (Componente Práctico)
Universidad Nacional Abierta y a Distancia (UNAD)
Estudiantes: Cristian Antonio Berrio Herrera
             Wendy Lorena Tarras Palacio
Grupo: 213023_133

Implementa:
- Abstracción, Herencia, Polimorfismo y Encapsulación
- Manejo avanzado de excepciones (personalizadas, try/except/else/finally, chaining)
- Sin bases de datos (listas en memoria + archivo de logs)
- Simulación de 20 operaciones (válidas e inválidas)
"""

from abc import ABC, abstractmethod   # Herramientas para crear clases abstractas
from datetime import datetime         # Fecha y hora para reservas y logs
import os                             # Para mostrar la ruta absoluta del log


# ==================== EXCEPCIONES PERSONALIZADAS ====================
class ErrorValidacion(Exception):
    """Excepción base para todos los errores de validación del sistema."""


class ClienteInvalidoError(ErrorValidacion):
    """Se lanza cuando los datos de un cliente no son válidos."""


class ClienteDuplicadoError(ClienteInvalidoError):
    """Se lanza cuando se intenta registrar una identificación ya existente."""


class ServicioNoDisponibleError(ErrorValidacion):
    """Se lanza cuando un servicio no existe, no está disponible o es inválido."""


class ReservaInvalidaError(ErrorValidacion):
    """Se lanza cuando una reserva no puede crearse o confirmarse."""


class OperacionNoPermitidaError(ErrorValidacion):
    """Se lanza cuando se intenta una transición de estado no permitida."""


class DatosIncompletosError(ErrorValidacion):
    """Se lanza cuando faltan parámetros obligatorios."""


class CalculoInconsistenteError(ErrorValidacion):
    """Se lanza cuando impuestos, descuentos o duración generan un cálculo absurdo."""


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
        # Al asignar se ejecutan los setters, que validan cada dato
        self.nombre = nombre
        self.identificacion = identificacion
        self.telefono = telefono
        self.email = email
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
        # Solo dígitos y mínimo 6
        if valor is None or not str(valor).isdigit() or len(str(valor)) < 6:
            raise ClienteInvalidoError(
                "La identificación debe ser numérica y tener al menos 6 dígitos.")
        self._identificacion = str(valor)

    @property
    def telefono(self):
        return self._telefono

    @telefono.setter
    def telefono(self, valor):
        # El teléfono es opcional; si se da, debe ser numérico de 7+ dígitos
        if valor and (not str(valor).isdigit() or len(str(valor)) < 7):
            raise ClienteInvalidoError(
                "El teléfono debe contener solo números y tener al menos 7 dígitos.")
        self._telefono = str(valor) if valor else ""

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, valor):
        # El email es opcional; si se da, debe tener formato usuario@dominio.ext
        if valor:
            valor = str(valor).strip()
            usuario, _, dominio = valor.partition("@")
            if not usuario or "." not in dominio or dominio.startswith(".") \
                    or dominio.endswith(".") or " " in valor:
                raise ClienteInvalidoError("El email no tiene un formato válido.")
        self._email = valor if valor else ""

    def validar(self):
        # Regla del negocio: nombre e identificación son obligatorios
        if not self._nombre or not self._identificacion:
            raise DatosIncompletosError("Nombre e identificación son obligatorios.")

    def obtener_descripcion(self):
        return f"Cliente: {self.nombre} | ID: {self.identificacion}"


# ==================== CLASE ABSTRACTA SERVICIO ====================
class Servicio(Entidad, ABC):
    """Clase abstracta de la que heredan todos los servicios de Software FJ."""

    def __init__(self, nombre, precio_base, disponible=True):
        # El nombre es obligatorio
        if not nombre or not str(nombre).strip():
            raise DatosIncompletosError("El nombre del servicio es obligatorio.")
        self.nombre = str(nombre).strip()
        # Conversión segura del precio: se encadena la excepción original (chaining)
        try:
            self.precio_base = float(precio_base)
        except (TypeError, ValueError) as e:
            raise ServicioNoDisponibleError(
                f"El precio '{precio_base}' no es un número válido.") from e
        self.disponible = disponible

    @abstractmethod
    def calcular_costo(self, duracion=1, impuesto=0.19, descuento=0.0):
        """Calcula el costo. Simula sobrecarga con parámetros opcionales:
        calcular_costo(2) | calcular_costo(2, 0.19) | calcular_costo(2, 0.19, 10)"""

    @abstractmethod
    def describir_servicio(self):
        """Descripción propia de cada servicio (polimorfismo)."""

    def validar(self):
        # Reglas comunes a todos los servicios
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
        if not isinstance(duracion, (int, float)) or duracion <= 0:
            raise ReservaInvalidaError("La duración debe ser un número mayor a cero.")
        if not 0 <= impuesto <= 1:
            raise CalculoInconsistenteError("El impuesto debe estar entre 0 y 1 (ej. 0.19).")
        if not 0 <= descuento <= 100:
            raise CalculoInconsistenteError("El descuento debe estar entre 0 y 100 (%).")
        subtotal = self.precio_base * duracion
        subtotal *= (1 + recargo / 100)            # Recargo propio del servicio
        con_descuento = subtotal * (1 - descuento / 100)
        return round(con_descuento * (1 + impuesto), 2)


# ==================== SERVICIOS ESPECIALIZADOS ====================
class ReservaSala(Servicio):
    """Reserva de salas (precio por hora). 5% extra de descuento desde 8 horas."""

    def calcular_costo(self, duracion=1, impuesto=0.19, descuento=0.0):
        if isinstance(duracion, (int, float)) and duracion >= 8:
            descuento = min(100, descuento + 5)    # Beneficio por jornada larga
        return self._calcular(duracion, impuesto, descuento)

    def describir_servicio(self):
        return f"Reserva de Sala | Precio/hora: ${self.precio_base:.2f} | Disponible: {self.disponible}"


class AlquilerEquipo(Servicio):
    """Alquiler de equipos (precio por día). Incluye 5% de recargo por seguro."""

    def calcular_costo(self, duracion=1, impuesto=0.19, descuento=0.0):
        return self._calcular(duracion, impuesto, descuento, recargo=5.0)

    def describir_servicio(self):
        return f"Alquiler de Equipo | Precio/día: ${self.precio_base:.2f} | Disponible: {self.disponible}"


class AsesoriaEspecializada(Servicio):
    """Asesoría especializada (precio por hora). Sin recargos ni beneficios."""

    def calcular_costo(self, duracion=1, impuesto=0.19, descuento=0.0):
        return self._calcular(duracion, impuesto, descuento)

    def describir_servicio(self):
        return f"Asesoría Especializada | Precio/hora: ${self.precio_base:.2f} | Disponible: {self.disponible}"


# ==================== CLASE RESERVA ====================
class Reserva:
    """Integra cliente, servicio, duración y estado (Pendiente→Confirmada→Procesada/Cancelada)."""

    def __init__(self, cliente, servicio, duracion, estado="Pendiente"):
        self.cliente = cliente
        self.servicio = servicio
        self.duracion = duracion
        self.estado = estado
        self.costo = 0.0
        self.fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    def confirmar(self, impuesto=0.19, descuento=0.0):
        """Calcula el costo y confirma. Encadena cualquier error con 'from e'."""
        if self.estado != "Pendiente":
            raise OperacionNoPermitidaError(
                f"No se puede confirmar una reserva en estado '{self.estado}'.")
        try:
            self.costo = self.servicio.calcular_costo(self.duracion, impuesto, descuento)
        except Exception as e:
            raise ReservaInvalidaError(f"No se pudo confirmar la reserva: {e}") from e
        else:
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

    def __init__(self):
        self.clientes = []     # Lista interna de clientes
        self.servicios = []    # Lista interna de servicios
        self.reservas = []     # Lista interna de reservas
        self.log_file = "logs_software_fj.txt"
        self._inicializar_log()

    def _inicializar_log(self):
        # Marca el inicio de cada sesión en el archivo de logs
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n=== INICIO DE SESIÓN: {datetime.now()} ===\n")

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

    def registrar_cliente(self, nombre, identificacion, telefono="", email=""):
        try:
            cliente = Cliente(nombre, identificacion, telefono, email)
            # Evita identificaciones repetidas
            if any(c.identificacion == cliente.identificacion for c in self.clientes):
                raise ClienteDuplicadoError(
                    f"Ya existe un cliente con la identificación {cliente.identificacion}.")
        except Exception as e:
            self.registrar_evento(f"Fallo al registrar cliente: {e}", es_error=True)
            raise
        else:
            self.clientes.append(cliente)
            self.registrar_evento(f"Cliente registrado: {cliente.obtener_descripcion()}")
            return cliente

    def crear_servicio(self, tipo, nombre, precio, disponible=True):
        try:
            clases = {"sala": ReservaSala, "equipo": AlquilerEquipo,
                      "asesoria": AsesoriaEspecializada}
            clase = clases.get(str(tipo).lower().strip())
            if clase is None:
                raise ServicioNoDisponibleError("Tipo de servicio no reconocido.")
            servicio = clase(nombre, precio, disponible)   # Polimorfismo: misma interfaz
            servicio.validar()
        except Exception as e:
            self.registrar_evento(f"Fallo al crear servicio: {e}", es_error=True)
            raise
        else:
            self.servicios.append(servicio)
            self.registrar_evento(f"Servicio creado: {servicio.describir_servicio()}")
            return servicio

    def crear_reserva(self, id_cliente, nombre_servicio, duracion, impuesto=0.19, descuento=0.0):
        try:
            cliente = next((c for c in self.clientes if c.identificacion == str(id_cliente)), None)
            if not cliente:
                raise ReservaInvalidaError("Cliente no encontrado.")
            servicio = next((s for s in self.servicios
                             if s.nombre.lower() == str(nombre_servicio).lower()), None)
            if not servicio:
                raise ServicioNoDisponibleError("Servicio no encontrado.")
            reserva = Reserva(cliente, servicio, duracion)
            reserva.confirmar(impuesto, descuento)
        except Exception as e:
            self.registrar_evento(f"Fallo al crear reserva: {e}", es_error=True)
            raise
        else:
            self.reservas.append(reserva)
            self.registrar_evento(
                f"Reserva #{len(self.reservas)} confirmada: {cliente.nombre} → "
                f"{servicio.nombre} | Costo: ${reserva.costo}")
            return reserva

    def _obtener_reserva(self, numero):
        """Busca una reserva por su número (1, 2, 3...)."""
        try:
            indice = int(numero) - 1
            if indice < 0:
                raise IndexError("índice negativo")
            return self.reservas[indice]
        except (ValueError, IndexError) as e:
            raise ReservaInvalidaError(f"La reserva #{numero} no existe.") from e

    def cancelar_reserva(self, numero):
        try:
            reserva = self._obtener_reserva(numero)
            reserva.cancelar()
        except Exception as e:
            self.registrar_evento(f"Fallo al cancelar reserva #{numero}: {e}", es_error=True)
            raise
        else:
            self.registrar_evento(f"Reserva #{numero} cancelada.")
            return reserva

    def procesar_reserva(self, numero):
        try:
            reserva = self._obtener_reserva(numero)
            reserva.procesar()
        except Exception as e:
            self.registrar_evento(f"Fallo al procesar reserva #{numero}: {e}", es_error=True)
            raise
        else:
            self.registrar_evento(f"Reserva #{numero} procesada.")
            return reserva

    def listar_todo(self):
        print("\n=== CLIENTES ===")
        for c in self.clientes:
            print(c.obtener_descripcion())
        print("\n=== SERVICIOS ===")
        for s in self.servicios:
            print(s.describir_servicio())   # Polimorfismo en acción
        print("\n=== RESERVAS ===")
        for i, r in enumerate(self.reservas, 1):
            print(f"#{i} | {r.cliente.nombre} | {r.servicio.nombre} | {r.duracion} | ${r.costo} | {r.estado}")


# ==================== SIMULACIÓN DE 20 OPERACIONES ====================
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
        ("Servicio Sala válido", lambda: sistema.crear_servicio("sala", "Sala Ejecutiva", 80.0)),
        ("Servicio Equipo válido", lambda: sistema.crear_servicio("equipo", "Laptop Gaming", 45.0)),
        ("Servicio Asesoría válida", lambda: sistema.crear_servicio("asesoria", "Consultoría Python", 120.0)),
        ("Servicio inválido (precio 0)", lambda: sistema.crear_servicio("sala", "Sala Pequeña", 0)),
        ("Servicio no disponible", lambda: sistema.crear_servicio("equipo", "Proyector", 30.0, disponible=False)),
        ("Reserva exitosa (con descuento)", lambda: sistema.crear_reserva("1023456789", "Sala Ejecutiva", 3, descuento=10)),
        ("Reserva con cliente inexistente", lambda: sistema.crear_reserva("999999", "Laptop Gaming", 2)),
        ("Reserva con servicio inexistente", lambda: sistema.crear_reserva("1023456789", "Servicio Fantasma", 1)),
        ("Reserva con duración inválida", lambda: sistema.crear_reserva("1023456789", "Consultoría Python", 0)),
        ("Reserva con descuento inconsistente", lambda: sistema.crear_reserva("52345678", "Laptop Gaming", 2, descuento=150)),
        ("Cancelar reserva #1", lambda: sistema.cancelar_reserva(1)),
        ("Cancelar reserva #1 otra vez (inválido)", lambda: sistema.cancelar_reserva(1)),
        ("Procesar reserva cancelada (inválido)", lambda: sistema.procesar_reserva(1)),
        ("Reserva exitosa de asesoría", lambda: sistema.crear_reserva("52345678", "Consultoría Python", 2)),
        ("Procesar reserva #2", lambda: sistema.procesar_reserva(2)),
    ]

    for i, (descripcion, operacion) in enumerate(operaciones, 1):
        print(f"\n--- Operación {i}: {descripcion} ---")
        try:
            operacion()
        except Exception as e:
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
        opcion = input("\nSeleccione una opción: ").strip()

        try:
            if opcion == "1":
                sistema.registrar_cliente(input("Nombre: "), input("Identificación: "),
                                          input("Teléfono (opcional): "), input("Email (opcional): "))
            elif opcion == "2":
                tipo = input("Tipo (sala/equipo/asesoria): ")
                nombre = input("Nombre del servicio: ")
                sistema.crear_servicio(tipo, nombre, input("Precio base: "))
            elif opcion == "3":
                id_c = input("Identificación del cliente: ")
                nom_s = input("Nombre del servicio: ")
                sistema.crear_reserva(id_c, nom_s, float(input("Duración: ")))
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
        except ValueError:
            print("Error controlado: debe ingresar un valor numérico válido.")
        except ErrorValidacion as e:
            print(f"Error controlado en el menú: {e}")
        except Exception as e:   # Última red de seguridad: el menú nunca se cae
            print(f"Error inesperado (el sistema continúa): {e}")


if __name__ == "__main__":
    print("Iniciando Sistema Software FJ...")
    menu_principal()
