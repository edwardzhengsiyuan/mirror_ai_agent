# Copyright (c) 2025 Siyuan Zheng
#
# All rights reserved.
#
# This software and associated documentation files (the "Software") are the
# proprietary and confidential information of Siyuan Zheng.
# Unauthorized copying, modification, distribution, public display, or
# public performance of this software is strictly prohibited.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# analysis/hehua/hehuichong_force_calculator.py

import numpy as np
from itertools import permutations

class HehuichongForceCalculator:
    def create_force_matrix(self, zhi_list, forces):
        n = len(forces)
        m = len(zhi_list)
        matrix = np.zeros((n, m))
        
        for i, force in enumerate(forces):
            if force.get_field == "地支":
                for element in force.elements:
                    j = zhi_list.index(element)
                    matrix[i][j] = force.E
        
        return matrix

    def calculate_net_forces(self, matrix):
        matrix = np.array(matrix)
        m, n = matrix.shape
        result = np.zeros_like(matrix, dtype=float)

        # 计算每一行的总和
        row_sums = np.sum(matrix, axis=1)

        # 对每一行进行处理
        for i in range(m):
            non_zero_indices = matrix[i] != 0
            non_zero_count = np.count_nonzero(non_zero_indices)

            # 计算其他行在这些列上的总和
            other_sums = np.sum(matrix[:, non_zero_indices], axis=0) - matrix[i, non_zero_indices]

            # 计算分配值
            redistribute_value = row_sums[i] - np.sum(other_sums)
            if non_zero_count > 0:
                redistributed_values = redistribute_value / non_zero_count
            else:
                redistributed_values = 0

            # 如果结果为负数，则置0
            redistributed_values = max(redistributed_values, 0)

            # 将分配值平均分配到原本不为0的元素上
            result[i, non_zero_indices] = redistributed_values

        return result

    def is_sorted_descending(self, lst):
        """检查列表是否按降序排序（忽略0）"""
        non_zero_lst = [x for x in lst if x != 0]
        return all(non_zero_lst[i] >= non_zero_lst[i + 1] for i in range(len(non_zero_lst) - 1))

    def is_valid_matrix(self, matrix):
        """检查矩阵每一列是否按降序排序（忽略0）"""
        for col in range(matrix.shape[1]):
            if not self.is_sorted_descending(matrix[:, col]):
                return False
        return True

    def generate_valid_matrices(self, matrix, row_indices):
        """生成所有满足条件的矩阵，并返回这些矩阵及其行索引"""
        for perm in permutations(row_indices):
            permuted_matrix = matrix[perm, :]
            if self.is_valid_matrix(permuted_matrix):
                yield permuted_matrix, list(perm)

    def find_valid_matrices_with_indices(self, matrix, indices):
        """封装的方法，传入矩阵及行索引，返回满足条件的矩阵及其行索引"""
        matrix = np.array(matrix)
        row_indices = list(indices)

        # 分离所有元素为0的行
        non_zero_row_mask = np.any(matrix != 0, axis=1)
        non_zero_matrix = matrix[non_zero_row_mask]
        zero_matrix = matrix[~non_zero_row_mask]
        non_zero_indices = [idx for idx, mask in zip(row_indices, non_zero_row_mask) if mask]
        zero_indices = [idx for idx, mask in zip(row_indices, non_zero_row_mask) if not mask]

        results = list(self.generate_valid_matrices(non_zero_matrix, range(len(non_zero_indices))))
        res = []
        idx = []
        if results:
            for result, perm_indices in results:
                # 将所有元素为0的行附加到矩阵的最后
                full_result = np.vstack([result, zero_matrix])
                full_indices = [non_zero_indices[i] for i in perm_indices] + zero_indices
                res.append(full_result)
                idx.append(full_indices)
        return res, idx

    def find_nonzero_conflict_rows(self, matrix, row_index):
        """查找与指定行在任意一列上都不为零的行"""
        conflict_rows = []
        for i in range(matrix.shape[0]):
            if i != row_index:
                for j in range(matrix.shape[1]):
                    if matrix[row_index, j] != 0 and matrix[i, j] != 0:
                        conflict_rows.append(i)
                        break
        return conflict_rows

    def process_matrix(self, matrix):
        """处理矩阵，返回留下的行的索引列表"""
        remaining_matrix = matrix.copy()
        original_indices = list(range(matrix.shape[0]))
        stored_indices = []
        while remaining_matrix.size > 0:
            current_row_index = 0  # 总是选择当前剩余矩阵的第一行
            stored_indices.append(original_indices[current_row_index])
            conflict_rows = self.find_nonzero_conflict_rows(remaining_matrix, current_row_index)
            # 删除冲突行及当前行
            indices_to_delete = conflict_rows + [current_row_index]
            remaining_matrix = np.delete(remaining_matrix, indices_to_delete, axis=0)
            # 更新原始索引列表
            original_indices = [idx for i, idx in enumerate(original_indices) if i not in indices_to_delete]
            # 检查剩余的行是否全为0
            if np.all(remaining_matrix == 0):
                remaining_matrix = np.empty((0, remaining_matrix.shape[1]))
                break
        return stored_indices

    def filter_rows(self, matrix, indices):
        """封装的方法，传入矩阵及行索引，返回留下的行的索引列表"""
        matrix = np.array(matrix)
        results = self.process_matrix(matrix)
        return [indices[i] for i in results]

    def remove_zero_rows(self, matrix, indices):
        """删除所有值为0的行，并返回新的矩阵及对应的索引列表"""
        matrix = np.array(matrix)
        non_zero_row_mask = np.any(matrix != 0, axis=1)
        filtered_matrix = matrix[non_zero_row_mask]
        filtered_indices = [idx for idx, mask in zip(indices, non_zero_row_mask) if mask]
        return filtered_matrix, filtered_indices

    def find_valid_forces(self, zhi_list, forces):
        self.zhi_list = zhi_list
        self.forces = forces
        self.matrix = self.create_force_matrix(zhi_list, forces)
        if self.matrix.size == 0:
            return [[]]
        m, n = self.matrix.shape
        net_forces = self.matrix

        # 生成所有可能的排序组合
        all_permutations, all_indices = self.find_valid_matrices_with_indices(net_forces, range(m))
        
        self.valid_combinations = []
        for perm_net_forces, idx in zip(all_permutations, all_indices):
            res = self.filter_rows(perm_net_forces, idx)
            valid_forces = [self.forces[i] for i in res]
            self.valid_combinations.append(valid_forces)
        return self.valid_combinations