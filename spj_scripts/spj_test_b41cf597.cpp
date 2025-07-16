#include <iostream>
#include <string>
#include <sstream>
#include <set>

using namespace std;

int main() {
    string input, expected_output, actual_output;
    
    getline(cin, input);
    getline(cin, expected_output);
    getline(cin, actual_output);
    
    try {
        // 解析输入和输出
        istringstream iss(input);
        set<string> input_numbers;
        string num;
        while (iss >> num) {
            input_numbers.insert(num);
        }
        
        istringstream oss(actual_output);
        set<string> output_numbers;
        while (oss >> num) {
            output_numbers.insert(num);
        }
        
        // 检查输出是否包含所有输入数字
        bool all_found = true;
        for (const string& input_num : input_numbers) {
            if (output_numbers.find(input_num) == output_numbers.end()) {
                all_found = false;
                break;
            }
        }
        
        if (all_found) {
            cout << "{\"status\": \"AC\", \"score\": 100, \"message\": \"输出正确\"}" << endl;
        } else {
            cout << "{\"status\": \"WA\", \"score\": 0, \"message\": \"输出错误\"}" << endl;
        }
        
    } catch (exception& e) {
        cout << "{\"status\": \"SPJ_ERROR\", \"score\": 0, \"message\": \"SPJ脚本执行错误\"}" << endl;
    }
    
    return 0;
}
