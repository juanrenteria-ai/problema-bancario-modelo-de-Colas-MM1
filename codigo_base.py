import numpy as np
import pandas as pd 
from scipy import stats 

class BankSimulation: 
    def __init__(self, num_cajeros=3, horas_operacion=8): 
        self.num_cajeros = num_cajeros 
        self.tiempo_simulacion = horas_operacion * 60 
        # Convertir a minutos # Probabilidades de tipo de acción 
        self.prob_retiro = 0.7 
        self.prob_pago = 0.3 
        # Probabilidades de tipo de usuario (dentro de cada acción)
        self.prob_usuario_retiro = [0.23, 0.40, 0.17, 0.20] 
        # Rápido, Normal, Lento, Muy lento 
        self.prob_usuario_pago = [0.10, 0.20, 0.30, 0.40] 
        # # Tiempos de servicio (media en minutos) 
        self.servicio_retiro = [1, 2, 3, 4]
        self.servicio_pago = [3, 3, 5, 7] 
        # # Tiempos de llegada (media en minutos) 
        self.llegada_retiro = [1, 2, 3, 3] 
        self.llegada_pago = [1, 2, 3, 4] 
        
    def generar_tiempo_exponencial(self, media):
         """Genera un tiempo aleatorio con distribución exponencial""" 
         return np.random.exponential(media) 
    
    def generar_tipo_accion(self): 
        """Determina si el cliente hace retiro o pago""" 
        return 'retiro' if np.random.random() < self.prob_retiro else 'pago' 
    
    def generar_tipo_usuario(self, tipo_accion): 
        """Determina el tipo de usuario (rápido, normal, lento, muy lento)""" 
        if tipo_accion == 'retiro': return np.random.choice([0, 1, 2, 3], p=self.prob_usuario_retiro) 
        else: return np.random.choice([0, 1, 2, 3], p=self.prob_usuario_pago) 
        
    def simular_dia(self, semilla=None): 
        """Simula un día de operación del banco""" 
        if semilla is not None: np.random.seed(semilla) 

        # Inicializar estadísticas
        clientes_atendidos = [] 
        tiempos_espera = [] 
        tiempos_sistema = [] 
        cajeros_ocupados = [0] * self.num_cajeros 
        cajeros_tiempo_libre = [0] * self.num_cajeros 

        # Lista de eventos futuros (tiempo, tipo, cajero) 
        
        eventos = []
        tiempo_actual = 0 
        
        # Generar primera llegada 
        tipo_accion = self.generar_tipo_accion()
        tipo_usuario = self.generar_tipo_usuario(tipo_accion) 
        
        if tipo_accion == 'retiro': 
            tiempo_llegada = self.generar_tiempo_exponencial(self.llegada_retiro[tipo_usuario])
        else: 
            tiempo_llegada = self.generar_tiempo_exponencial(self.llegada_pago[tipo_usuario]) 
        eventos.append((tiempo_llegada, 'llegada', tipo_accion, tipo_usuario, None)) 
        
        # Cola de clientes esperando 
        cola = [] 
        
        while tiempo_actual < self.tiempo_simulacion: 
            if not eventos: break 
            
            # Obtener próximo evento 
            eventos.sort(key=lambda x: x[0]) 
            evento = eventos.pop(0) 
            tiempo_actual = evento[0] 
            if tiempo_actual > self.tiempo_simulacion: 
                break 
            tipo_evento = evento[1]
            
            if tipo_evento == 'llegada': 
                tipo_accion = evento[2] 
                tipo_usuario = evento[3] 
                
                # Buscar cajero disponible 
                cajero_disponible = None 
                for i in range(self.num_cajeros): 
                    if cajeros_ocupados[i] == 0: cajero_disponible = i 
                    break 
                if cajero_disponible is not None: 
                    
                    # Asignar a cajero disponible 
                    cajeros_ocupados[cajero_disponible] = 1 
                    # Generar tiempo de servicio 
                    if tipo_accion == 'retiro': 
                        tiempo_servicio = self.generar_tiempo_exponencial(self.servicio_retiro[tipo_usuario]) 
                    else: 
                        tiempo_servicio = self.generar_tiempo_exponencial(self.servicio_pago[tipo_usuario]) 
                    # Programar fin de servicio 
                    tiempo_fin = tiempo_actual + tiempo_servicio 
                    eventos.append((tiempo_fin, 'fin_servicio', tipo_accion, tipo_usuario, cajero_disponible)) 
                    
                    # Registrar estadísticas 
                    clientes_atendidos.append({ 'tipo_accion': tipo_accion, 'tipo_usuario': tipo_usuario, 'tiempo_espera': 0, 'tiempo_servicio': tiempo_servicio, 'cajero': cajero_disponible }) 
                else: 
                    # Agregar a cola 
                    cola.append((tiempo_actual, tipo_accion, tipo_usuario)) 
                    
                    # Generar próxima llegada 
                tipo_accion_nueva = self.generar_tipo_accion()
                tipo_usuario_nuevo = self.generar_tipo_usuario(tipo_accion_nueva) 
                    
                if tipo_accion_nueva == 'retiro': 
                    tiempo_llegada = tiempo_actual + self.generar_tiempo_exponencial( self.llegada_retiro[tipo_usuario_nuevo]) 

                else: 
                    tiempo_llegada = tiempo_actual + self.generar_tiempo_exponencial( self.llegada_pago[tipo_usuario_nuevo]) 
                eventos.append((tiempo_llegada, 'llegada', tipo_accion_nueva, tipo_usuario_nuevo, None)) 
                    
            elif tipo_evento == 'fin_servicio': 
                cajero = evento[4] 
                cajeros_ocupados[cajero] = 0 
                
                # Si hay clientes en cola, atender al siguiente 
                if cola: 
                    cliente_cola = cola.pop(0) 
                    tiempo_llegada_cola = cliente_cola[0] 
                    tipo_accion_cola = cliente_cola[1] 
                    tipo_usuario_cola = cliente_cola[2] 
                    tiempo_espera = tiempo_actual - tiempo_llegada_cola 
                    cajeros_ocupados[cajero] = 1 
                    
                    if tipo_accion_cola == 'retiro':
                         tiempo_servicio = self.generar_tiempo_exponencial( self.servicio_retiro[tipo_usuario_cola]) 

                    else: 
                        tiempo_servicio = self.generar_tiempo_exponencial( self.servicio_pago[tipo_usuario_cola]) 
                        tiempo_fin = tiempo_actual + tiempo_servicio 
                        eventos.append((tiempo_fin, 'fin_servicio', tipo_accion_cola, tipo_usuario_cola, cajero)) 
                        clientes_atendidos.append({ 'tipo_accion': tipo_accion_cola, 'tipo_usuario': tipo_usuario_cola, 'tiempo_espera': tiempo_espera, 'tiempo_servicio': tiempo_servicio, 'cajero': cajero }) 
                        return pd.DataFrame(clientes_atendidos) 
                    
        def ejecutar_replicas(self, num_replicas=10): 
            """Ejecuta múltiples réplicas de la simulación""" 
            resultados = [] 
            for i in range(num_replicas): 
                print(f"Ejecutando réplica {i+1}/{num_replicas}...") 
                df = self.simular_dia(semilla=i) 
                df['replica'] = i + 1 
                resultados.append(df) 
                return pd.concat(resultados, ignore_index=True)
            
            # Ejemplo de uso 

            if __name__ == "__main__": 
                sim = BankSimulation(num_cajeros=3, horas_operacion=8) 
                resultados = sim.ejecutar_replicas(num_replicas=10) 
                # Análisis de resultados 
                print("\n=== ANÁLISIS DE RESULTADOS ===\n") 
                
                # Punto 1: Cajero con menor y mayor tiempo de atención 

                tiempos_por_cajero = resultados.groupby('cajero')['tiempo_servicio'].mean()
                print("Tiempo promedio de servicio por cajero:") 
                print(tiempos_por_cajero) 
                print(f"\nCajero más rápido: Cajero {tiempos_por_cajero.idxmin()} ({tiempos_por_cajero.min():.2f} min)") 
                print(f"Cajero más lento: Cajero {tiempos_por_cajero.idxmax()} ({tiempos_por_cajero.max():.2f} min)") 
                
                # Punto 2: Promedio de usuarios por tipo 

                usuarios_por_tipo = resultados.groupby(['tipo_accion', 'tipo_usuario']).size() 
                print("\n\nUsuarios por tipo:") 
                print(usuarios_por_tipo) 
                
                # Guardar resultados 
                
                resultados.to_excel('resultados_simulacion_banco.xlsx', index=False) 
                print("\n\nResultados guardados en 'resultados_simulacion_banco.xlsx'")