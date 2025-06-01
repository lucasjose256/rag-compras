document.addEventListener('DOMContentLoaded', () => {
    const chatBox = document.getElementById('chatBox');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const flaskApiUrl = 'http://127.0.0.1:5000/chat'; // URL da sua API Flask

    // Função para adicionar mensagem à caixa de chat
    function addMessage(text, sender, messageElement) {
        let p;
        if (messageElement) { // Se um elemento de mensagem já existe (para streaming)
            p = messageElement.querySelector('p');
            if (p) { // Garante que o parágrafo exista
                p.textContent += text; // Adiciona texto ao parágrafo existente
            } else { // Se o parágrafo não existir por algum motivo, cria um (fallback)
                const newP = document.createElement('p');
                newP.textContent = text;
                messageElement.appendChild(newP);
            }
        } else { // Cria um novo elemento de mensagem
            const newMessageDiv = document.createElement('div');
            newMessageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'bot-message');
            
            p = document.createElement('p');
            p.textContent = text;
            newMessageDiv.appendChild(p);
            
            chatBox.appendChild(newMessageDiv);
            messageElement = newMessageDiv; // Retorna o novo elemento para atualizações futuras
        }
        chatBox.scrollTop = chatBox.scrollHeight; // Auto-scroll para a última mensagem
        return messageElement; // Retorna o elemento da mensagem para possíveis atualizações
    }

    // Função para enviar mensagem para a API e receber resposta em stream
    async function sendMessageToBot() {
        const messageText = userInput.value.trim();
        if (messageText === '') {
            return; 
        }

        addMessage(messageText, 'user'); 
        userInput.value = ''; 

        let botMessageElement = null; // Para armazenar o elemento da mensagem do bot e atualizá-lo
        // Adiciona uma mensagem de "Bot está digitando..."
        const typingIndicator = document.createElement('div');
        typingIndicator.classList.add('message', 'bot-message', 'typing-indicator');
        const pTyping = document.createElement('p');
        pTyping.textContent = 'Bot está digitando...';
        typingIndicator.appendChild(pTyping);
        chatBox.appendChild(typingIndicator);
        chatBox.scrollTop = chatBox.scrollHeight;

        try {
            const response = await fetch(flaskApiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: messageText }),
            });
            
            // Remove o indicador "Bot está digitando..." assim que a resposta (headers) chegar
            if (chatBox.contains(typingIndicator)) { // Verifica se ainda existe
                chatBox.removeChild(typingIndicator);
            }

            if (!response.ok) {
                const errorText = await response.text(); // Tenta ler o corpo do erro como texto
                console.error('[FETCH ERROR RAW]', errorText); // Log do erro cru
                addMessage(`Erro ${response.status}: ${errorText || response.statusText}`, 'bot');
                return;
            }
            console.log('[FETCH] Resposta OK, iniciando leitura do stream.'); // Log

            // Lida com o corpo da resposta como um stream de texto
            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8'); // Garante a decodificação correta
            let firstChunk = true;
            let receivedAnything = false; // Flag para verificar se algo foi recebido

            // Loop para ler o stream
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) {
                    console.log('[STREAM] Leitura finalizada (done=true).'); // Log
                    if (!receivedAnything && !botMessageElement) { // Se nada foi recebido E nenhum balão de bot foi criado
                        console.log('[STREAM] Nenhum dado recebido antes do stream finalizar.');
                        addMessage("O bot não enviou uma resposta ou a resposta foi vazia.", 'bot');
                    }
                    break; 
                }
                
                receivedAnything = true; // Marcar que recebemos dados
                const chunkText = decoder.decode(value, { stream: true }); // Decodifica o chunk
                console.log('[STREAM] Chunk recebido e decodificado:', chunkText); // Log do chunk no console do navegador

                if (chunkText) { // Processa apenas se o chunk decodificado não for vazio
                    if (firstChunk) {
                        botMessageElement = addMessage(chunkText, 'bot'); // Cria a mensagem do bot com o primeiro chunk
                        firstChunk = false;
                    } else {
                        addMessage(chunkText, 'bot', botMessageElement); // Adiciona aos chunks subsequentes
                    }
                }
            }
             // Se o stream terminar e a última mensagem do decoder não foi processada
            const remainingText = decoder.decode(); // Pega qualquer texto restante no buffer do decoder
            if (remainingText) {
                console.log('[STREAM] Texto restante no decoder:', remainingText); // Log
                if (botMessageElement) { 
                    addMessage(remainingText, 'bot', botMessageElement);
                } else if (receivedAnything) { 
                    addMessage(remainingText, 'bot');
                }
            }


        } catch (error) {
            console.error('[STREAM CATCH ERROR] Erro na comunicação ou processamento do stream:', error); // Log detalhado do erro
            // Remove o indicador "Bot está digitando..." também em caso de erro
            if (chatBox.contains(typingIndicator)) {
                 chatBox.removeChild(typingIndicator);
            }
            // Adiciona a mensagem de erro
            if (botMessageElement) { 
                 addMessage(` (Erro de conexão: ${error.message})`, 'bot', botMessageElement);
            } else {
                 addMessage(`Não foi possível conectar ao bot. Verifique sua conexão ou o servidor. Detalhes: ${error.message}`, 'bot');
            }
        }
    }

    sendButton.addEventListener('click', sendMessageToBot);
    userInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessageToBot();
        }
    });
});