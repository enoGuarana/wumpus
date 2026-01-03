import google.generativeai as genai
import json
import time

# --- CONFIGURAÇÃO ---
# ⚠️ SUBSTITUA PELA SUA CHAVE DO GOOGLE AI STUDIO
MINHA_CHAVE = "CHAVE ENOMOTO-COLE_SUA_AQUI" 

genai.configure(api_key=MINHA_CHAVE)

# --- 1. O MUNDO (SIMULADOR) ---
class WumpusWorld:
    def __init__(self):
        # Grid 4x4: (x,y) FAZER WUMPUS GERAR CAMPO ALEATORIO
        # S=Seguro, P=Poço, W=Wumpus, O=Ouro
        

    def get_sensors(self):
        """Retorna o que o agente sente na posição atual"""
        percepts = []
        x, y = self.agent_pos
        
        if self.grid.get((x,y)) == "O": percepts.append("Brilho")
        
        vizinhos = [(x+1,y), (x-1,y), (x,y+1), (x,y-1)]
        for nx, ny in vizinhos:
            obj = self.grid.get((nx, ny))
            if obj == "P": percepts.append("Brisa")
            if obj == "W": percepts.append("Fedor")
            
        return percepts if percepts else ["Nada"]

    def move(self, action):
        """Executa o movimento físico"""
        x, y = self.agent_pos
        
        if action == "PEGAR":
            return "Pegou Ouro" if self.grid.get((x,y)) == "O" else "Nada aqui"
        
        if action == "CIMA": y += 1
        elif action == "BAIXO": y -= 1
        elif action == "DIR": x += 1
        elif action == "ESQ": x -= 1
        
        # Paredes
        if x < 1 or x > 4 or y < 1 or y > 4: return "Parede"
            
        self.agent_pos = (x, y)
        obj = self.grid.get((x,y))
        
        if obj == "P": return "Morreu (Poço)"
        if obj == "W": return "Morreu (Wumpus)"
        return "Moveu"

# --- 2. MEMÓRIA & RAG ---
class AgentMemory:
    def __init__(self):
        self.log = [] 
        self.visited = set([(1,1)])

    def add_event(self, pos, sensors, action):
        self.log.append({"pos": pos, "sensors": sensors, "action": action})
        self.visited.add(pos)

    def get_rag_context(self, current_pos):
        """FILTRA apenas o que importa: O que eu vi nas casas vizinhas?"""
        x, y = current_pos
        vizinhos = [(x, y+1), (x, y-1), (x+1, y), (x-1, y)]
        
        contexto = []
        for entry in self.log:
            if entry['pos'] in vizinhos:
                contexto.append(f"- Vizinho {entry['pos']}: Senti {entry['sensors']}")
            elif entry['pos'] == current_pos:
                contexto.append(f"- Aqui mesmo {entry['pos']}: Senti {entry['sensors']}")
                
        return "\n".join(contexto) if contexto else "Nenhuma informação dos arredores."

# --- 3. O AGENTE COM GEMINI ---
class GeminiAgent:
    def __init__(self):
        self.memory = AgentMemory()
        # Usando o modelo Flash que é mais rápido e eficiente para lógica simples
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def think(self, current_pos, current_sensors):
        # A. RAG - Recuperação
        contexto = self.memory.get_rag_context(current_pos)
        
        # B. Prompt Engineering
        prompt = f"""
        Você é um robô jogando Wumpus World. Seja lógico e cauteloso.
        
        REGRAS:
        1. Sente 'Brisa' -> Poço vizinho.
        2. Sente 'Fedor' -> Wumpus vizinho.
        3. Sente 'Brilho' -> Ouro aqui -> Ação: PEGAR.
        4. Se não sente nada, os vizinhos são seguros.
        
        MEMÓRIA RECUPERADA (Dicas):
        {contexto}
        
        SITUAÇÃO ATUAL:
        - Posição: {current_pos}
        - Sensores: {current_sensors}
        - Já visitei: {list(self.memory.visited)}
        
        Responda APENAS um JSON válido neste formato, sem markdown:
        {{ "raciocinio": "explicação breve", "acao": "CIMA/BAIXO/ESQ/DIR/PEGAR" }}
        """

        # C. Geração (Chamada API)
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Limpeza e Parsing do JSON
            texto = response.text.strip()
            # Às vezes o modelo manda ```json ... ```, vamos limpar
            texto = texto.replace("```json", "").replace("```", "")
            dados = json.loads(texto)
            
            # Grava na memória
            self.memory.add_event(current_pos, current_sensors, dados['acao'])
            return dados
            
        except Exception as e:
            print(f"Erro Gemini: {e}")
            return {"raciocinio": "Erro de conexão", "acao": "CIMA"}

# --- 4. EXECUÇÃO ---
def main():
    if "COLE_SUA" in MINHA_CHAVE:
        print("❌ ERRO: Você esqueceu de colocar sua Chave de API no código!")
        return

    mundo = WumpusWorld()
    agente = GeminiAgent()
    
    print("🤖 --- INICIANDO GEMINI NO WUMPUS ---")
    
    for i in range(1, 15):
        pos = mundo.agent_pos
        sensores = mundo.get_sensors()
        
        print(f"\n📍 TURNO {i} | Em {pos} | Vê: {sensores}")
        
        decisao = agente.think(pos, sensores)
        
        print(f"🧠 {decisao['raciocinio']}")
        print(f"👉 Ação: {decisao['acao']}")
        
        resultado = mundo.move(decisao['acao'])
        print(f"📢 Resultado: {resultado}")
        
        if "Morreu" in resultado:
            print("💀 GAME OVER")
            break
        if "Pegou" in resultado:
            print("🏆 VITÓRIA! O GEMINI PEGOU O OURO!")
            break
            
        time.sleep(1) # Pausa dramática para ler o console

if __name__ == "__main__":
    main()